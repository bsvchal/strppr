## Requirements

- Python 3
- Copy `.env.example` and update the Stripe API keys

## How to run

1. Create and activate a new virtual environment

**MacOS / Unix**

```
python3 -m venv env
source env/bin/activate
```

**Windows (PowerShell)**

```
python3 -m venv env
.\env\Scripts\activate.bat
```

2. Install dependencies

```
pip install -r requirements.txt
```

3. Export and run the application
Adding `export FLASK_ENV=development` to your env will enable Flask to automatically reload changes without having to restart the server.

**MacOS / Unix**

```
export FLASK_APP=server.py
export FLASK_ENV=development
python3 -m flask run --port=4242
```

**Windows (PowerShell)**

```
$env:FLASK_APP=“server.py"
$env:FLASK_ENV="development"
python3 -m flask run --port=4242
```

4. Go to `localhost:4242` in your browser
