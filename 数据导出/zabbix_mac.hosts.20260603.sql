--
-- PostgreSQL database dump
--

\restrict Ik09Hdd8edUh0BpfaVKGthcjrdlZ7T9cbAfwqPxAx15u48STa4EXm6bkgeDniFT

-- Dumped from database version 14.22
-- Dumped by pg_dump version 14.22

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'SQL_ASCII';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: hosts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hosts (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    system character varying(100),
    subsystem character varying(100),
    template_name character varying(255)
);


--
-- Name: hosts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.hosts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hosts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.hosts_id_seq OWNED BY public.hosts.id;


--
-- Name: hosts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hosts ALTER COLUMN id SET DEFAULT nextval('public.hosts_id_seq'::regclass);


--
-- Data for Name: hosts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.hosts (id, name, description, created_at, updated_at, system, subsystem, template_name) FROM stdin;
1	Zabbix server	Local Zabbix server	2026-04-21 17:07:03.284849	2026-04-21 17:07:03.284849	上市系统	上市日常监管模块	21001
2	10.24.3.12	Test server 1	2026-04-21 17:07:03.284849	2026-04-21 17:07:03.284849	上市系统	上市日常监管模块	21001
3	10.24.3.23		2026-04-24 15:33:45.646743	2026-04-24 15:33:45.646743	上市系统	上市日常监管模块	21001
\.


--
-- Name: hosts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.hosts_id_seq', 4, true);


--
-- Name: hosts hosts_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hosts
    ADD CONSTRAINT hosts_name_key UNIQUE (name);


--
-- Name: hosts hosts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hosts
    ADD CONSTRAINT hosts_pkey PRIMARY KEY (id);


--
-- Name: idx_hosts_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hosts_name ON public.hosts USING btree (name);


--
-- PostgreSQL database dump complete
--

\unrestrict Ik09Hdd8edUh0BpfaVKGthcjrdlZ7T9cbAfwqPxAx15u48STa4EXm6bkgeDniFT

