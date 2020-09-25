# wasabi-api
Backend is a REST API built around [FastAPI](https://github.com/tiangolo/fastapi) framework. To be deployed in serverless environment via [mangum](https://github.com/erm/mangum) adapter.

## Installation
```shell
pipenv --three
pipenv shell
pipenv install --dev
pipenv run dev-setup
```


## Run
### Launch development server
To run [uvicorn](https://github.com/encode/uvicorn) ASGI server:
```shell
pipenv run dev
```
### Production server
The production ASGI server is wrapped with [mangum](https://github.com/erm/mangum) adapter and can be deployed as Lambda function.

## License
[MIT](LICENSE)