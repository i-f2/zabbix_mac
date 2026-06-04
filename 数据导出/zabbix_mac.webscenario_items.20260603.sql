--
-- PostgreSQL database dump
--

\restrict 6BsS0UIMaitYSH41k23fZ92AR1FivxYuAmUOq9rcUJcUT2loJcls65G9ettJWky

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
-- Name: webscenario_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webscenario_items (
    id integer NOT NULL,
    system character varying(100) NOT NULL,
    subsystem character varying(100) NOT NULL,
    nginx_clb character varying(255),
    nginx character varying(255),
    clb character varying(255),
    pod character varying(255),
    webtest_api character varying(255) NOT NULL,
    webtest_nginx_api character varying(255) NOT NULL,
    in_room character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: webscenario_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.webscenario_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: webscenario_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.webscenario_items_id_seq OWNED BY public.webscenario_items.id;


--
-- Name: webscenario_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webscenario_items ALTER COLUMN id SET DEFAULT nextval('public.webscenario_items_id_seq'::regclass);


--
-- Data for Name: webscenario_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.webscenario_items (id, system, subsystem, nginx_clb, nginx, clb, pod, webtest_api, webtest_nginx_api, in_room, created_at, updated_at) FROM stdin;
1	Test System	Test Subsystem	192.168.1.1:8080	192.168.1.2:8080	192.168.1.3:8080	192.168.1.4:8080	/api/test	/nginx/api/test	Room A	2026-04-24 17:50:52.977611	2026-04-24 17:50:52.977611
2	Another System	Another Subsystem	192.168.2.1:8080	192.168.2.2:8080	192.168.2.3:8080	192.168.2.4:8080	/api/another	/nginx/api/another	Room B	2026-04-24 17:50:52.977611	2026-04-24 17:50:52.977611
\.


--
-- Name: webscenario_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.webscenario_items_id_seq', 2, true);


--
-- Name: webscenario_items webscenario_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webscenario_items
    ADD CONSTRAINT webscenario_items_pkey PRIMARY KEY (id);


--
-- Name: idx_webscenario_items_subsystem; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webscenario_items_subsystem ON public.webscenario_items USING btree (subsystem);


--
-- Name: idx_webscenario_items_system; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webscenario_items_system ON public.webscenario_items USING btree (system);


--
-- PostgreSQL database dump complete
--

\unrestrict 6BsS0UIMaitYSH41k23fZ92AR1FivxYuAmUOq9rcUJcUT2loJcls65G9ettJWky

