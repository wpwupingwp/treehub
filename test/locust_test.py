from locust import HttpUser, between, task


class WebSiteUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def index(self):
        self.client.get("/")

    @task
    def list_all(self):
        self.client.get("/tree/list_all")

    @task
    def query(self):
        self.client.get("/tree/query")

    @task
    def list_s(self):
        self.client.get("/submit/list")
