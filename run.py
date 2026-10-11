import os

from app import create_app


app = create_app()


if __name__ == '__main__':
    host = os.environ.get(
        'QUANTUMREADY_HOST',
        '127.0.0.1'
    )

    port = int(
        os.environ.get(
            'QUANTUMREADY_PORT',
            5000
        )
    )

    debug = os.environ.get(
        'QUANTUMREADY_DEBUG',
        'false'
    ).lower() == 'true'

    app.run(
        host=host,
        port=port,
        debug=debug
    )