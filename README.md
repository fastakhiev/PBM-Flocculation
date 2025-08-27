## Project launch
1. **Clone the repository**
    ```shell
    git clone https://github.com/fastakhiev/PBM-Flocculation-Tool
    ```
   
2. **Create .env file in backend/.env**
    ```shell
   POSTGRES_USER=
   POSTGRES_PASSWORD=
   POSTGRES_PORT=
   POSTGRES_HOST=
   POSTGRES_DB=
   REDIS_HOST=
   REDIS_PORT=
    ```
3. **Run**
    ```
    docker-compose up -d --build
    ```
4. **Run migrations in the backend container**
   ```
   alembic upgrade head
   ```
