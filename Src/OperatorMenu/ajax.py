#!/usr/bin/env python
#-*- coding:UTF-8 -*-

from flask import (Flask, 
                    render_template,
                    request, 
                    jsonify, 
                    json)
import configparser

app = Flask(__name__)
config = configparser.ConfigParser()


@app.route("/data")
def webapi():
    return render_template("data-try.html")
    # return render_template("data.html")


@app.route("/data/message", methods=["GET"])
def getDataSetting():
    if request.method == "GET":
        data = config.read('static/data/setting.ini')
        # with open("static/data/setting.ini", "r") as f:
        #     data = cfg.read(f)
        #     # print("text : ", data)
        # f.close
        print(f'Title: {config[BASIC][TITLE]}')
        return jsonify(data)  # 直接回傳 data 也可以，都是 json 格式
        

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


if __name__ == '__main__':
    app.run()
