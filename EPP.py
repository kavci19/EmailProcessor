import imaplib
import email
import html2text
import requests
import base64
import urllib.parse
from urllib.parse import urlencode



host = 'imap.gmail.com'
username = '' #enter email address to parse emails from
password = '' #password for email address
customer_id = 'cus_MnJwQGN8m9dHIF' #enter customer id and api key for commercial use (this one is just for testing)
api_key = 'd3426844-a56a-4e37-bba4-e08b5e945342'
url_quote = 'https://api.postmates.com/' + 'v1/customers/' + customer_id + '/delivery_quotes'
url_delivery = 'https://api.postmates.com/' + 'v1/customers/' + customer_id + '/deliveries'

def get_inbox():
    mail = imaplib.IMAP4_SSL(host)
    mail.login(username, password)
    mail.select("inbox")
    _, search_data = mail.search(None, 'UNSEEN')
    my_message = []
    for num in search_data[0].split():
        email_data = {}
        _, data = mail.fetch(num, '(RFC822)')
        # print(data[0])
        _, b = data[0]
        email_message = email.message_from_bytes(b)
        for header in ['subject', 'to', 'from', 'date']:
            #print("{}: {}".format(header, email_message[header]))
            email_data[header] = email_message[header]
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True)
                email_data['body'] = body.decode()
            elif part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True)
                email_data['html_body'] = html_body.decode()
        my_message.append(email_data)
    return my_message

def find_order_id(content):

    for i in range(len(content)):
        if 'Order' in content[i] and 'Id' in content[i+1]:
            number = content[i+2]
            number = number[2:-1]
            if number[-1] == '*':
                number = number[:-1]
            if number[-1] == ')':
                number = number[:-1]
            return number

def find_order_time(content):

    for i in range(len(content)):
        if 'Date' in content[i]:
            return content[i+2]

def find_order_sku(content):

    sku = []
    for i in range(len(content)):
        if 'SKU' in content[i]:
            sku.append(content[i+1])
    return sku

def find_order_quantities(content):
    quantities = []

    for i in range(len(content)):

        if 'Qty' in content[i]:
            quantities.append(content[i+1])
    return quantities


def find_order_delivery_address(content):
    address = ''

    for i in range(len(content)):
        if 'Delivery' in content[i] and 'Address' in content[i+1]:
            i+=2
            while (not 'Contact' in content[i]) and (not 'Billing' in content[i]):
                address+=content[i] + ' '
                i+=1

            if len(address) > 1:
                address = address[:-2]

            return address





def find_order_pickup_address(content):
    address = ''
    hs = ''
    mobile = ''
    mobileNos = ''
    for i in range(len(content)):
        if 'Delivery' in content[i] and 'From' in content[i+1]:
            i+=2
            while (not 'Contact' in content[i]) and (not 'Billing' in content[i]) and (not 'Mobile' in content[i]):
                address+=content[i] + ' '
                i+=1

            if 'Mobile' in content[i] and 'No' in content[i+1]:
                mobileNos = content[i+2].split(',')
                mobile = mobileNos[0]

            if len(address) > 1:
                address = address[:-2]

            addList = address.split()

            for i in addList:
                if i.isnumeric():
                    break
                else:
                    hs += i + ' '

            return address, hs, mobile






def find_order_customer_name_phone(content):
    name = ''
    phone = ''
    for i in range(len(content)-1):
        if 'Billing' in content[i] and 'Address' in content[i+1]:
            i +=2
            while i < len(content) and not content[i].isdigit():
                name += content[i] + ' '
                i+=1
            while i < len(content) and not 'Contact' in content[i]:
                i+=1
            if i < len(content):
                phone = content[i+1]

            if len(name) > 1:
                name = name[:-2]

            return name, phone



def determine_product_size(skus):
    sizes = []

    for sku in skus:

        if sku[-1] == 'S' or sku[-1] == 's':
            sizes.append('small')
        elif sku[-1] == 'M' or sku[-1] == 'm':
            sizes.append('medium')
        elif sku[-1] == 'L' or sku[-1] == 'l':
            sizes.append('large')
        elif sku[-1] == 'X' or sku[-1] == 'x':
            sizes.append('extra large')
        else:
            sizes.append('medium')

    return sizes



def find_product_names(content, isHtml):
    products = []

    for i in range(len(content) - 1):
        if 'SKU' in content[i]:
            if (isHtml):
                i+=6
            else:
                i+=3
            product = ''
            while not 'Qty' in content[i]:
                product += content[i] + ' '
                i+=1
            products.append(product)

    return products


def find_tip(content, isHtml):

    for i in range(len(content)-1):
        if 'Tip' in content[i]:
            if isHtml:
                return content[i+2]
            else:
                return content[i+1]


def find_pickup_time(content):
    for i in range(len(content)):
        if 'Pickup' in content[i] and 'Time' in content[i+1]:
            return content[i+3] + ' ' + content[i+4]

def build_manifest_items(product_list, quantity_list, size_list):

    manifest = []
    for i in range(len(product_list)):
        dict = {}
        dict["name"] = product_list[i]
        dict["quantity"] = int(quantity_list[i])
        dict["size"] = size_list[i]
        manifest.append(dict)
    return manifest


if __name__ == "__main__":
    my_inbox = get_inbox()
    email_num = 1
    isHtml = False

    for email in my_inbox:
        try:
            if not 'You have an order from Tooler' in email['subject']:
                continue
            print('Email ' + str(email_num))
            email_num+=1
            if 'body' in email:
                content = email['body'].split()
            else:
                content = email['html_body']
                text = html2text.html2text(content)
                content = text.split()
                isHtml = True

            delivery_address = str(find_order_delivery_address(content))
            sku = find_order_sku(content)
            customer_name, customer_phone = find_order_customer_name_phone(content)
            order_id = find_order_id(content)
            order_time = find_order_time(content)
            quantities = find_order_quantities(content)
            product_sizes = determine_product_size(sku)
            product_names = find_product_names(content, isHtml)
            pickup_address, hardware_store, hs_mobile = find_order_pickup_address(content)
            tip = find_tip(content, isHtml)
            pickup_time = find_pickup_time(content)
            manifest = build_manifest_items(product_names, quantities, product_sizes)
            usrPass = api_key + ':'
            data_bytes = usrPass.encode("utf-8")
            b64Val = base64.b64encode(data_bytes).decode('utf-8')


            print('Order ID: ' + order_id )
            print('Time: ' + order_time)
            print('SKU: ' + str(sku))
            print('Product Names: ' + str(product_names))
            print('Quantities: ' + str(quantities))
            print('Sizes: ' + str(product_sizes))
            print('Delivery Address: ' + delivery_address)
            print('Customer Name: ' + str(customer_name))
            print('Customer Phone: ' + str(customer_phone))
            print('Pickup Address: ' + str(pickup_address))
            print('Hardware Store: ' + hardware_store)
            print('Hardware Store Mobile: ' + hs_mobile)
            print('Tip: ' + tip)
            print('Pickup Time: ' + pickup_time)

            if len(delivery_address) == 0:
                print('Product is pickup only. No request made to Postmates.')

            else:



                data = {
                    'dropoff_address': '1178 Broadway, New York, NY, USA',
                    'pickup_address': pickup_address
                }

                response = requests.post(url_quote, data=data, auth=(api_key, ''))
                print()
                print('Data sent to Postmates Quote API: ')
                print(data)
                print()
                print('Quote response: ')
                print(response.json())

                if response.status_code == 200:

                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Authorization': 'Basic ' + b64Val
                    }

                    manifest = str(manifest)
                    manifest = manifest.replace("'",'"')

                    #check if phone has 10 digits, if not use tooler phone
                    customer_phone = '+19175959184'

                    data = {
                        'dropoff_address': delivery_address,
                        'dropoff_name': str(customer_name),
                        'dropoff_phone_number': str(customer_phone),
                        'manifest': 'Construction supplies',
                        'pickup_address': str(pickup_address),
                        'pickup_name': str(hardware_store),
                        'pickup_phone_number': str(hs_mobile),
                        'manifest_items': manifest,
                    }

                    payload = urllib.parse.urlencode(data, quote_via=urllib.parse.quote)

                    print()
                    print('Data sent to Postmates Delivery API: ')
                    print(data)
                    response = requests.post(url_delivery, data=payload, headers=headers)
                    print()
                    print('Delivery response: ')
                    print(response.content)



            print('\n\n\n')
        except:
            print('Error parsing email')
            continue

# print(search_data)