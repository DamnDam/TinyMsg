import click
import requests
from . import app

@click.command()
@click.option('--host', '-H', help='Host to serve on', type=str, default='0.0.0.0')
@click.option('--port', '-P', help='Port to serve on', type=int, default=5000)
def serve(host, port):
    app.run(host=host, port=port, debug=False)

@click.command()
@click.option('--message', '-m', help='Message to post', type=str)
@click.option('--host', '-H', help='Host to post to', type=str, default='localhost')
@click.option('--port', '-P', help='Port to post to', type=int, default=5000)
def post(message, host, port):
    requests.post(f'http://{host}:{port}', data=message)
