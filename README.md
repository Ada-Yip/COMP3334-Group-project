# E2EE SNS

注意事項:
database.py 中的資料如果會同其他地方重疊,加 "_db" suffix<br>

function 入面可以直接加"""description"""做comment<br>

可以用post取代get<br>

client接收response時使用_request_json_來統一格式<br>

server: main.py     or uvicorn server.api_server:app --reload<br>

client: client/app.py<br>

authorization format : "Bearer tokens"<br>

Message projection:<br>
    Server side: use logger to print message<br>
    Client side: print client response or use "print"<br>
