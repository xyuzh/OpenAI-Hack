1. Set up python env
```
poetry init 
poetry env use {/opt/homebrew/bin/python3}
poetry env activate
poetry install
```

```
brew install mongodb-community@7.0
brew services start mongodb-community@7.0

brew services stop mongodb-community@7.0
brew install --cask mongodb-compass

pgweb --bind=0.0.0.0 --port=8081 --url=postgres://postgres:test@localhost:5432
```
