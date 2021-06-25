# IDrive

## Notes


## Build

```
docker build -t $(basename $(pwd)) --build-arg POSTGRES_USER=$POSTGRES_USER --build-arg POSTGRES_PASSWORD=$POSTGRES_PASSWORD .
```

## Run


```
docker run -d --volumes-from --name=$(basename $(pwd))-c $(basename $(pwd))

```