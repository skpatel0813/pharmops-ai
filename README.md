# docker-compose.yml
services:
  postgres:
    image: postgres:18
    container_name: pharmops_postgres
    environment:
      POSTGRES_USER: pharmops
      POSTGRES_PASSWORD: pharmops
      POSTGRES_DB: pharmops_db
    ports:
      - "5432:5432"
    volumes:
      - pharmops_data:/var/lib/postgresql/data

volumes:
  pharmops_data: