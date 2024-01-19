from .tinymsg import app

# CLI handler to run the app
def run():
    app.run(host='0.0.0.0', port=5000, debug=False)