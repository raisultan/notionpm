## Usefule links
- [Accessing Notion API with Python](https://thienqc.notion.site/Notion-API-Python-ca0fd21bc224492b8daaf37eb06289e8)
- [Notion API Guide JS](https://developers.notion.com/docs/getting-started)
- [Notion API Raw Docs](https://developers.notion.com/reference)
- [Notion Postman](https://www.postman.com/notionhq/workspace/notion-s-api-workspace/overview)
- [Notion Python Client](https://github.com/ramnes/notion-sdk-py)

## Useful Redis commands
```shell
# pull redis image
docker pull redis

# LOCAL run redis
docker run --name notionpm-redis -d -p 6379:6379 redis

# access redis-cli
docker exec -it notionpm-redis redis-cli
```

## Redis RDB

Here is a step-by-step guide on how to use the Redis Docker image with RDB setup:

1. Install Docker: Follow the official Docker installation guide for your operating system: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)
2. Pull the Redis image: Open your terminal or command prompt and run the following command to download the Redis image from Docker Hub:

```bash
docker pull redis

```

1. Prepare a directory for Redis data: Create a directory on your host machine where Redis will store its RDB snapshots. For example:

```bash
mkdir /root/redis-data

```

1. Run the Redis container with RDB configuration: Run the following command to start a Redis container with RDB persistence enabled. Replace `/root/redis-data` with the path to the directory you created in step 3. You can also adjust the time interval and the number of write operations that should trigger a snapshot, as needed.

```bash
docker run --name notionpm-redis -p 6379:6379 -v /root/redis-data:/data -d redis redis-server --save 60 1 --slave-read-only no

```

In this example, a snapshot will be created every 60 seconds if at least one write operation occurs.

1. Connect to the Redis container: To interact with the Redis container, you can use the `redis-cli` tool. First, install `redis-cli` on your host machine following the instructions here: [https://redis.io/topics/rediscli](https://redis.io/topics/rediscli)

Next, use the following command to connect to the running Redis container:

```bash
docker exec -it notionpm-redis redis-cli

```

1. Perform Redis operations: Once connected, you can issue Redis commands to store and retrieve data. For example:

```bash
SET key1 "Hello, Redis!"
GET key1

```

1. Verify the RDB snapshot: After some time (based on your `-save` configuration), you should see an RDB snapshot file in the `/root/redis-data` directory. The file will be named `dump.rdb`.
2. Stop the Redis container: When you're done using Redis, stop the container by running:

```bash
docker stop notionpm-redis

```

1. Restart the Redis container with existing data: To restart the Redis container and load the existing RDB snapshot, run the same command as in step 4:

```bash
docker run --name notionpm-redis -p 6379:6379 -v /root/redis-data:/data -d redis redis-server --save 60 1 --slave-read-only no

```

This will start a new Redis container, load the RDB snapshot from the `/path/to/redis-data` directory, and continue using the RDB persistence method.

With this setup, you have successfully configured a Redis Docker container with RDB persistence.
