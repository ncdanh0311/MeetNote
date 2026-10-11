"""Run the local MeetNote web application."""

from meetnote import create_app


app = create_app()


if __name__ == "__main__":
    print(f"MeetNote đang chạy tại http://{app.config['HOST']}:{app.config['PORT']}")
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=False,
        use_reloader=False,
    )
