from flask import Flask, render_template,request, jsonify
import threading
import new_monitor as scrapper
import datetime

app = Flask(__name__)
@app.route('/')
def home():
    return render_template('home.html')



@app.route('/start', methods=['POST'])
def start():
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
                   message="Success",
                   statusCode=202,
                   data='Job Accepted. User will be Notified via Email'), 202



if __name__ == '__main__':
    app.run(debug=True)