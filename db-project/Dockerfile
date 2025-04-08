FROM mysql:8

# run command file
CMD [ "mysql", "-u", "root", "-p", "password", "-e", "source /docker-entrypoint-initdb.d/01_init.sql" ]