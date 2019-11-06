import logging
logging.basicConfig(format='%(asctime)s - %(levelname)s:%(name)s : %(message)s',level=logging.DEBUG)



from flask import Flask, render_template,request, jsonify
import threading
import qantas_monitor as scrapper
import datetime


app = Flask(__name__)

rootlog = logging.getLogger('werkzeug')
rootlog.setLevel(logging.ERROR)

rootlog = logging.getLogger('selenium')
rootlog.setLevel(logging.ERROR)

rootlog = logging.getLogger('urllib3')
rootlog.setLevel(logging.ERROR)



@app.route('/')
def home():
    # if scrapper.is_job_running():
    #
    #     return render_template('job_running.html')
    # else:
    #     return render_template('home.html')

    return render_template('home.html')



@app.route('/start', methods=['POST'])
def start():

    if scrapper.is_job_running():
        return jsonify(isError=True,
                       data='Job Already Running. Please wait for it to finish.'), 200


    start_day = request.json.get('start_day')
    end_day = request.json.get('end_day')
    routes = request.json.get('routes')

    # print( request.form)
    # print(request.json)
    job_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    thread1 = threading.Thread(target=scrapper.run, args=(routes, int(start_day),int(end_day)), kwargs={'job_id': job_id})
    thread1.start()


    print(start_day,end_day,routes)



    return jsonify(isError=False,
                   jobId=job_id,
                   data='Job Accepted. User will be Notified via Email'), 200



if __name__ == '__main__':
    app.run(debug=True)