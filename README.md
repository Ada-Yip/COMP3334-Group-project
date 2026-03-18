# E2EE SNS

注意事項:
database.py 中的資料如果會同其他地方重疊,加 "_db" suffix
function 入面可以直接加"""description"""做comment
可以用post取代get
client接收response時使用_request_json_來統一格式
server: main.py     or uvicorn server.api_server:app --reload
client: client/app.py