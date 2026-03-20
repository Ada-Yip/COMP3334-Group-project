# E2EE SNS

注意事項:
database.py 中的資料如果會同其他地方重疊,加 "_db" suffix\n
function 入面可以直接加"""description"""做comment\n
可以用post取代get\n
client接收response時使用_request_json_來統一格式\n
server: main.py     or uvicorn server.api_server:app --reload\n
client: client/app.py\n
authorization format : "Bearer tokens"\n
Message projection:
    Server side: use logger to print message\n
    Client side: print client response or use "print"\n