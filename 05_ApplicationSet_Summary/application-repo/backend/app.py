from flask import Flask  
from flask_cors import CORS  
from redis import Redis  
import os  
  
app = Flask(__name__)  
  
# Allow CORS requests explicitly from frontend at localhost:8080  
cors_allowed_origin = os.getenv("CORS_ALLOWED_ORIGIN", "http://localhost:8080")  
  
CORS(app, resources={r"/api/*": {"origins": cors_allowed_origin}})  
#CORS(app)

redis_conn_str = os.getenv("REDIS_CONN_STR", "redis://localhost:6379")  
  
@app.route('/api/health')  
def health():  
    return 'ok', 200  
  
@app.route('/api/redis')  
def redis_health():  
    try:  
        redis = Redis.from_url(redis_conn_str)  
        redis.ping()  
        return 'ok', 200  
    except Exception as e:  
        return 'error', 500  
  
if __name__ == '__main__':  
    app.run(host='0.0.0.0', port=5000)  