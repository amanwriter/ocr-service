var spawn = require('child_process').spawn,
child = spawn('java', ['-jar', 'Tc.jar']);

var handler = function(req, res) {
if (req.method=='POST'){
var body = '';
        req.on('data', function (data) {
            body += data;
        });
        req.on('end', function () {
			tr_path = body.split('\n');
			for (var i = 0; i< tr_path.length-1; i++){
				var end = Date.now() + 10;
				if (tr_path[i]=="1 0 0"){end+=100;}
				while (Date.now()<end){}
				child.stdin.write(tr_path[i]+"\n");	
			}			
        });

res.writeHead(200);
res.end("ok");}
}


var app = require('http').createServer(handler);
app.listen(8000);
