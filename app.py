from flask import Flask, render_template,request, jsonify
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

    print(start_day,end_day,routes)

    return jsonify(isError=False,
                   message="Success",
                   statusCode=200,
                   data='User will be Notified via Email'), 200



if __name__ == '__main__':
    app.run(debug=True)