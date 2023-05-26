# Notifications (a.k.a. Webhooks)

Notifications (often also called webhooks) are used to asynchronously send updates about events from one server to another.

The Speechmatics API can be configured to send notifications to your server when your submitted job completes. These notifications will contain configurable information about the status and configuration of the job. Full details of this configuration can be found [in the Docs](https://docs.speechmatics.com/features-other/notifications).

In this example, we demonstrate the principle of using notifications to create a robust production-ready integration with the Speechmatics API. Please note, however, that these examples are NOT production-grade code.

We employ a common pattern with three components:

1. A client which sends out jobs
2. A server which receives the webhooks
3. A cronjob script which periodically syncs your data store with the Speechmatics API in case of notification failure

For the sake of simplicity, these code examples employ sqlite3 as a datastore because of its inclusion in the python standard library. We recommend using a production grade DB such as PostgreSQL, MySQL, Mongodb etc. in your own systems.

## Getting Started

To get started, make sure you have installed python >= 3.7. Then run:

```
pip install -r requirements.txt
```

Also make sure the speechmatics CLI tool is installed and run the following command, which will set your auth token for you. Note that you can also set the auth token in the code, examples of which are provided [in the docs](https://docs.speechmatics.com/introduction/batch-guide)

```
speechmatics config set --auth-token {YOUR_AUTH_TOKEN}
```

You can get an API key from our [portal](https://portal.speechmatics.com/manage-access/). You will also need to replace the URL placeholder in client.py with your own, public-facing URL from which server.py will be run. If you are just hacking locally, you can consider using [webhook.site](https://webhook.site), which will allow you to forward requests to local host from the browser session.

Once this configuration has been done, open a new terminal session wherever you have chosen to run your server and run:
```
python server.py
```
to start the server. Then run:
```
python client.py
```

After a few seconds, you should see the webhook request received by the server. There should also be a new file, `{job_id}.json`, in your server-side file system, with all the transcript json present.

In case the webhook failed to come through, you can run:
```
python cronjob.py
```
to synchronise your system with our API.
