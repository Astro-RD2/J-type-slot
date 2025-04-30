#!/usr/bin/env python
#-*- coding:UTF-8 -*-

from flask import (Flask, 
                    render_template,
                    request, 
                    jsonify, 
                    json)
import configparser
import subprocess

app = Flask(__name__)
# config = configparser.ConfigParser()


@app.route("/data")
def webapi():
    return render_template("data-try.html")
    # return render_template("data.html")


@app.route("/data/message", methods=["GET"])
def getDataSetting():
    config = configparser.ConfigParser()                   
    if request.method == "GET":        
        # with open("static/data/message.json", "r") as f:
        #     data = json.load(f)
        #     print("text : ", data)
        # f.close

        data = {}
        config.read('static/data/setting.ini', encoding='UTF-8')
        

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
            "BILL_ACCEPTOR_PORT": config['DEVICE']['BILL_ACCEPTOR_PORT']            
        }

        print("it is a console")
        data = json.dumps(data)
        return jsonify(data)  # 直接回傳 data 也可以，都是 json 格式
        #return data

@app.route('/data/message', methods=['POST'])
def setDataMessage():
    if request.method == "POST":
        data = {
            'appInfo': {
                'id': request.form['app_id'],
                'name': request.form['app_name'],
                'version': request.form['app_version'],
                'author': request.form['app_author'],
                'remark': request.form['app_remark']
            }
        }
        print(type(data))
        with open('static/data/input.json', 'w') as f:
            json.dump(data, f)
        f.close
        return jsonify(result='OK')

@app.route('/data/network', methods=['POST'])
def setnetwork():
    if request.method == "POST":
        
        # subprocess.run(['python', 'form1.py'])

        config = configparser.ConfigParser()
        config.read('static/data/setting.ini', encoding='UTF-8')

        bootprot = request.form.get('BOOTPROT')

        if bootprot == "static":
            ipaddr = request.form['IPADDR_f1']
            netmask = request.form['NETMASK_f1']
            gateway = request.form['GATEWAY_f1']
        else:
            bootprot = "dhcp"

        config.set('NETWORK', 'BOOTPROT', bootprot)
        if bootprot == "static":
            config.set('NETWORK', 'IPADDR', ipaddr)
            config.set('NETWORK', 'NETMASK', netmask)
            config.set('NETWORK', 'GATEWAY', gateway)

        with open('static/data/setting.ini', 'w') as configfile:
            config.write(configfile)
        
    return 'Script executed successfully!'

@app.route('/data/basicdata', methods=['POST'])
def setbasicdata():
    print(request.form)
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

    config = configparser.ConfigParser()
    config.read('static/data/setting.ini', encoding='UTF-8') 

    config.set('BASIC', 'TITLE', title)
    config.set('BASIC', 'REMARK', remark)
    config.set('BASIC', 'TIME_ZONE', time_zone)
    config.set('BASIC', 'TIME_FORMAT', time_format)
    config.set('BASIC', 'CURRENCY_SYMBOL', currency_symbol)
    config.set('BASIC', 'CURRENCY_SYMBOL_PRINT_SIDE', cs_print_side)
    config.set('BASIC', 'THOUSAND_SEPARATOR', thousand_separator)
    config.set('BASIC', 'HOME_URL', home_url)
    # config.set('BASIC', 'TITLE', apientry)
    config.set('BASIC', 'ASSET', asset)

    with open('static/data/setting.ini', 'w') as configfile:
        config.write(configfile)
    
    return 'Script executed successfully!'


if __name__ == '__main__':
    app.run()
