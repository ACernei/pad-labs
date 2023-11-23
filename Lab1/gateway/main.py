from icecream import ic

from flask import Flask, jsonify
import concurrent.futures

from controllers.workout_controller import workout_controller
from controllers.diet_controller import diet_controller


app = Flask(__name__)

app.register_blueprint(workout_controller)
app.register_blueprint(diet_controller)

MAX_CONCURRENT_TASKS = 5
executor = concurrent.futures.ThreadPoolExecutor(MAX_CONCURRENT_TASKS)

@app.route('/gateway_status', methods=['GET'])
def get_gateway_status():
    return jsonify({'status': 'Gateway is up and running'})

    
if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0', threaded=True)