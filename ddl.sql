-- create user and database from root
-- psql -U postgres
--
-- postgres=# create user tapp with password '****'
-- postgres=# create database tapp owner tapp
--
-- (after above commands)
-- psql -U tapp -d tapp -f ddl.sql
-- -> Done!

-- cache for queries
create table queries
(   id varchar(512) constraint firstkey primary key,
    seq text not null,
    created_date date not null);

create index query_index
on queries (id);

-- cache for results
create table results
(   id varchar(512) primary key,
    result JSON,
    mail_address_hash varchar(512),
    calculated timestamp);

create index result_index
on results (id);
