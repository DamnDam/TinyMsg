import click


# We use click to create a command line interface for our application.
@click.group()
def main():
    pass


@main.command()
@click.option("--host", "-H", help="Host to serve on", type=str, default="0.0.0.0")
@click.option("--port", "-P", help="Port to serve on", type=int, default=5000)
def serve(host, port):
    from .tinymsg import create_app

    create_app().run(host=host, port=port, debug=False)


@main.command()
@click.option("--message", "-m", help="Message to post", type=str)
@click.option("--host", "-H", help="Host to post to", type=str, default="localhost")
@click.option("--port", "-P", help="Port to post to", type=int, default=5000)
def post(message, host, port):
    import requests

    print(requests.post(f"http://{host}:{port}", data=message, timeout=1))
