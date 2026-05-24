# Yandex AI Studio — настройка

1. Ключ API: [aistudio.yandex.ru → разработчикам](https://aistudio.yandex.ru/ru/developers) → создать API-ключ.

2. **ID каталога** (`YANDEX_FOLDER_ID`):
   - [console.yandex.cloud](https://console.yandex.cloud/) → облако → **Каталог** → ID вида `b1gai2s8u8p5vdje63jo`.
   - В API запросах модель задаётся URI: `gpt://b1gai2s8u8p5vdje63jo/yandexgpt`.

3. В `.env` (любой из вариантов):

   ```env
   YANDEX_API_KEY=AQVN…
   YANDEX_FOLDER_ID=b1gai2s8u8p5vdje63jo
   YANDEX_MODEL=yandexgpt
   ```

   Или только URI в модели (folder подставится сам):

   ```env
   YANDEX_API_KEY=AQVN…
   YANDEX_MODEL=gpt://b1gai2s8u8p5vdje63jo/yandexgpt
   ```

   Модели: `yandexgpt`, `yandexgpt-lite`, `yandexgpt-pro` (иногда с суффиксом `/latest`).

4. В дашборде: **Настройки → API** → вписать Folder ID и модель → **Сохранить API** → **Проверить Yandex**.

5. Проверка в терминале: `tender-leads yandex check`

6. Агенты на Yandex: в `.env` `AGENT_PROVIDER=yandex` или **Настройки → Проект → провайдер yandex**.

7. **Responses API** (`YANDEX_USE_RESPONSES_API=true`) на `llm.api.cloud.yandex.net` даёт **404** — используйте **Chat Completions** (`false`, по умолчанию). При включённом Responses клиент сам переключится на chat/completions.
