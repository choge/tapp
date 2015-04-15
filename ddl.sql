create table queries
(   id char(8) constraint firstkey primary key,
    mail_address varchar(256) not null,
    created_date date not null);

create index query_index
on queries (id);

create table query_details
(   id char(8) not null,
    detail_id char(8) not null,
    seq text not null,
    primary key (id, detail_id));

create index detail_id
on query_details (id, detail_id);
