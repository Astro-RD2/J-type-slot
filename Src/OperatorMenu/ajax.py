#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os
from flask import (Flask, 
                    render_template,
                    redirect, 
                    url_for,
                    request, 
                    jsonify, 
                    json)
import configparser

app = Flask(__name__)
configfile = 'setting.ini'
config = configparser.ConfigParser()

@app.route("/data")
def homebase():
    global configfile

    # if configure file for development, ..
    if os.path.isfile('./static/data/setting.ini'):
        configfile = './static/data/setting.ini'
    # if configure file for product, ..
    elif os.path.isfile('../../data/setting.ini'):
        configfile = './static/data/setting.ini'
    else:
        print('configure file not found!!')
        return f'configure file not found!'

    try:
        # for development
        config.read(configfile, encoding='UTF-8')
    except Exception as e:    
        print('except:', e)
        return f'configure file ead rerror! {e}'

    return render_template("data.html")

@app.route("/data/message", methods=["GET"])
def getDataSetting():
    #config = configparser.ConfigParser()                   
    if request.method == "GET": 
        data = {}
        '''
        # if configure file for development, ..
        if os.path.isfile('./static/data/setting.ini'):
            configfile = './static/data/setting.ini'
        # if configure file for product, ..
        elif os.path.isfile('../../data/setting.ini'):
            configfile = './static/data/setting.ini'
        else:
            print('configure file not found!!')
            return f'configure file not found!'

        try:
            # for development
            config.read(configfile, encoding='UTF-8')
        except Exception as e:    
            print('except:', e)
            return f'configure file ead rerror! {e}'
        '''

        try:
            data = { 
                "TITLE": config['BASIC']['TITLE'],
                "REMARK": config['BASIC']['REMARK'],
                "TIME_ZONE_LIST": config['BASIC']['TIME_ZONE_LIST'],
                "TIME_ZONE": config['BASIC']['TIME_ZONE'],
                "TIME_FORMAT_LIST": config['BASIC']['TIME_FORMAT_LIST'],
                "TIME_FORMAT": config['BASIC']['TIME_FORMAT'],
                "CURRENCY_SYMBOL_LIST": config['BASIC']['CURRENCY_SYMBOL_LIST'],
                "CURRENCY_SYMBOL": config['BASIC']['CURRENCY_SYMBOL'],
                "CURRENCY_SYMBOL_PRINT_SIDE": config['BASIC']['CURRENCY_SYMBOL_PRINT_SIDE'],
                "THOUSAND_SEPARATOR": config['BASIC']['THOUSAND_SEPARATOR'],
                "HOME_URL": config['BASIC']['HOME_URL'],
                "HOME_URL1": config['BASIC']['HOME_URL1'],
                "HOME_URL2": config['BASIC']['HOME_URL2'],
                "ASSET": config['BASIC']['ASSET'],
                "BOOTPROT": config['NETWORK']['BOOTPROT'],
                "IPADDR": config['NETWORK']['IPADDR'],
                "NETMASK": config['NETWORK']['NETMASK'],
                "GATEWAY": config['NETWORK']['GATEWAY'],
                "ACCOUNT": config['REGISTER']['ACCOUNT'],
                "TOKEN": config['REGISTER']['TOKEN'],
                "TOKEN_LAST_TS": config['REGISTER']['TOKEN_LAST_TS'],
                # "BILL_ACCEPTOR_PORT": config['DEVICE']['BILL_ACCEPTOR_PORT']            
            }
        except Exception as e:
            print('except:', e)
            return f'configure file key error! {e}'

        data = json.dumps(data)
        return jsonify(data)  # 直接回傳 data 也可以，都是 json 格式
        #return data

@app.route('/data/<section_id>', methods=['POST'])
def setIniData(section_id):
    '''
    config = configparser.ConfigParser()
    config.read('static/data/setting.ini', encoding='UTF-8') 
    '''

    # NETWORK
    if section_id == "NETWORK":
        bootprot = request.form.get('BOOTPROT')

        if bootprot == "static":
            ipaddr = request.form['IPADDR_f1']
            netmask = request.form['NETMASK_f1']
            gateway = request.form['GATEWAY_f1']
        else:
            bootprot = "dhcp"

        # update
        config.set(section_id, 'BOOTPROT', bootprot)
        if bootprot == "static":
            # for reference: config[section_id]['IPADDR'] = ipaddr
            config.set(section_id, 'IPADDR', ipaddr)
            config.set(section_id, 'NETMASK', netmask)
            config.set(section_id, 'GATEWAY', gateway)

    # BASIC
    elif section_id == "BASIC":
        title = request.form['TITLE_f2']
        remark = request.form['REMARK_f2']
        time_zone = request.form.get('TIME_ZONE')
        time_format = request.form.get('TIME_FORMAT')
        currency_symbol = request.form.get('CURRENCY_SYMBOL')
        cs_print_side = request.form.get('CURRENCY_SYMBOL_PRINT_SIDE')
        thousand_separator = request.form.get('THOUSAND_SEPARATOR')    
        home_url = request.form.get('HOME_URL')
        apientry = request.form['apientry']
        asset = request.form['ASSET_f2']

        # update
        config.set(section_id, 'TITLE', title)
        config.set(section_id, 'REMARK', remark)
        config.set(section_id, 'TIME_ZONE', time_zone)
        config.set(section_id, 'TIME_FORMAT', time_format)
        config.set(section_id, 'CURRENCY_SYMBOL', currency_symbol)
        config.set(section_id, 'CURRENCY_SYMBOL_PRINT_SIDE', cs_print_side)
        config.set(section_id, 'THOUSAND_SEPARATOR', thousand_separator)
        config.set(section_id, 'HOME_URL', home_url)
        # config.set(section_id, 'TITLE', apientry)
        config.set(section_id, 'ASSET', asset)

    # REGISTER
    elif section_id == "REGISTER":
        account = request.form['ACCOUNT_f3']
        #update
        config.set(section_id, 'ACCOUNT', account)
    else:
        pass

    try:
        with open(configfile, 'w') as f:
            config.write(f, space_around_delimiters=False)
    except Exception as e:
        print('except:', e)
        # return and show message
        return f"Drop {e}"
    
    # 'homebase' is the function name for your /data route
    if section_id == "REGISTER" and request.form['submit_button'] == "drop":
        # Redirect or handle cancel logic
        return "Drop"
    else:
        return redirect(url_for("homebase"))
    

if __name__ == '__main__':
    app.run()
