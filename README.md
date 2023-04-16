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

# run redis
docker run --name notionpm-redis -v /root/redis/data:/data -v /root/redis/redis.conf:/usr/local/etc/redis/redis.conf -p 6379:6379 -d redis redis-server /usr/local/etc/redis/redis.conf

# access redis-cli
docker exec -it notionpm-redis redis-cli
````
