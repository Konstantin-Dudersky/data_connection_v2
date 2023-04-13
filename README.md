# Синхронизация данных через Redis.

В приложении создаются объекты datapoint. При создании datapoint добавляются в коллекцию .... Изменения отслеживаются, и отправляются в redis.

Каждый datapoint имеет уникальный UUID. По нему связываются данные. 

Данные из redis можно получить как по UUID, так и по pub/sub.

Данные хранятся в 2 коллекциях:

- datapoint_collection - заполняется в методе `__init__ ` при создании нового datapoint
- last_sync - буфер для контроля, какие datapoint поменялись и требуется отправить

Последовательность синхронизации с redis:

- итерируемся по ключам в datapoint_collection, если ключ не найден в last_sync - значит datapoint еще никогда не считывался. Выполняем команду HGET. Успешный результат сохраняем в dp_local. Обновляем datapoint_collection
- проверяем данные по подписке. Результат сохраняем в last_sync. Обновляем datapoint_collection
- итерируемся по ключам в datapoint_collection:
  - если ключ не найден в dp_local - выполняем HSET
  - если найден - выполняем HSET, если необходимо

Признак, что данные полученные из redis (dp_redis) данные можно копировать в локальную память (dp_local):

- dp_local.ts_write > dp_redis.ts_read + DELAY => ничего не копируем, выходим из проверки
- dp_local.ts_read < dp_redis.ts_read => копируем read
- dp_local.ts_write < dp_redis.ts_write => копируем write

Признак, что локальные данные (dp_local) можно копировать в redis (dp_redis). Данные посылаются через dp_send:

- dp_local.ts_read + DELAY < dp_redis.ts_write + DELAY => ничего не копируем, выходим из проверки
- dp_local.ts_read > dp_redis.ts_read => копируем read в dp_send
- dp_local.ts_write > dp_redis.ts_write => копируем write в dp_send
- посылаем dp_send, если есть необходимость, и сохраняем в dp_redis

