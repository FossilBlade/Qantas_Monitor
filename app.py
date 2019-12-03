import logging
logging.basicConfig(format='%(levelname)s --> %(message)s', level=logging.INFO)
rootlog = logging.getLogger('werkzeug')
rootlog.setLevel(logging.ERROR)

rootlog = logging.getLogger('selenium')
rootlog.setLevel(logging.ERROR)

rootlog = logging.getLogger('urllib3')
rootlog.setLevel(logging.ERROR)



import os,shutil


from flask import Flask, render_template, request, jsonify
import threading
import qantas_monitor as scrapper
import datetime

app = Flask(__name__)



if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
    print('DELETE CACHED FOLDER')
    shutil.rmtree('chrome-profile',ignore_errors=True)

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/start', methods=['POST'])
def start():

    if scrapper.is_job_running():
        return jsonify(isError=True,
                       data='Job Already Running. Please wait for it to finish.'), 200

    start_day = request.json.get('start_day')
    end_day = request.json.get('end_day')
    routes = request.json.get('routes')

    if not start_day or not end_day:
        return jsonify(isError=True,
                       data='Please enter both start day and end day'), 200


    try:
        start_day = int(start_day)
        end_day = int(end_day)
    except TypeError:
        return jsonify(isError=True,
                       data='Start day and/or End day entered are not integers. Please enter integer values.'), 200


    if start_day>=end_day:
        return jsonify(isError=True,
                       data='Start day cannot be greater than or equal to end day. Please enter valid values.'), 200

    # print( request.form)
    # print(request.json)
    job_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    thread1 = threading.Thread(target=scrapper.run, args=(routes, start_day, end_day),
                               kwargs={'job_id': job_id})
    thread1.start()

    # print(start_day, end_day, routes)

    return jsonify(isError=False,
                   jobId=job_id,
                   data='Job Accepted. User will be Notified via Email'), 200


if __name__ == '__main__':
    from waitress import serve

    serve(app, listen='*:5000')

    # app.run(debug=True)
