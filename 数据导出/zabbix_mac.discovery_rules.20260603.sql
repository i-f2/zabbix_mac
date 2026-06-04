--
-- PostgreSQL database dump
--

\restrict pZgTBctkuWtOEy4TatUM4ZP4TbNRcQNwnMle7fw5Ld0Ixmy2MPITXK9Hc297tfW

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
-- Name: discovery_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discovery_rules (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    key character varying(255) NOT NULL,
    delay character varying(50) NOT NULL,
    evaltype integer DEFAULT 0,
    status integer DEFAULT 0,
    template_name character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: discovery_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.discovery_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: discovery_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.discovery_rules_id_seq OWNED BY public.discovery_rules.id;


--
-- Name: discovery_rules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discovery_rules ALTER COLUMN id SET DEFAULT nextval('public.discovery_rules_id_seq'::regclass);


--
-- Data for Name: discovery_rules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discovery_rules (id, name, key, delay, evaltype, status, template_name, created_at, updated_at) FROM stdin;
1	Block devices discovery	vfs.dev.discovery	1h	0	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
2	Mounted filesystem discovery	vfs.fs.discovery	1h	0	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
\.


--
-- Name: discovery_rules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.discovery_rules_id_seq', 2, true);


--
-- Name: discovery_rules discovery_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discovery_rules
    ADD CONSTRAINT discovery_rules_pkey PRIMARY KEY (id);


--
-- Name: idx_discovery_rules_template; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_discovery_rules_template ON public.discovery_rules USING btree (template_name);


--
-- PostgreSQL database dump complete
--

\unrestrict pZgTBctkuWtOEy4TatUM4ZP4TbNRcQNwnMle7fw5Ld0Ixmy2MPITXK9Hc297tfW

