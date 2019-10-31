from flask import Flask, render_template,request, jsonify
import threading
import new_monitor as scrapper

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

    thread1 = threading.Thread(target=scrapper.run, args=(routes, int(start_day),int(end_day)))
    thread1.start()


    print(start_day,end_day,routes)

    # thread1.join()

    return jsonify(isError=False,
                   message="Success",
                   statusCode=202,
                   data='Job Accepted. User will be Notified via Email'), 202



if __name__ == '__main__':
    app.run(debug=True)