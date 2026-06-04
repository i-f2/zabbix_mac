--
-- PostgreSQL database dump
--

\restrict 7AfmxffBcVNuhxR5G1faiKjNye4EV9xW54FWHmzJNXSjxnRYb9fMMAHkl9I4CrN

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
-- Name: host_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.host_templates (
    id integer NOT NULL,
    host_id integer NOT NULL,
    template_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: host_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.host_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: host_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.host_templates_id_seq OWNED BY public.host_templates.id;


--
-- Name: host_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_templates ALTER COLUMN id SET DEFAULT nextval('public.host_templates_id_seq'::regclass);


--
-- Data for Name: host_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.host_templates (id, host_id, template_id, created_at) FROM stdin;
6	1	2	2026-04-24 15:30:05.529296
7	2	2	2026-04-24 15:30:11.369041
9	3	2	2026-04-24 15:34:24.213349
\.


--
-- Name: host_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.host_templates_id_seq', 9, true);


--
-- Name: host_templates host_templates_host_id_template_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_templates
    ADD CONSTRAINT host_templates_host_id_template_id_key UNIQUE (host_id, template_id);


--
-- Name: host_templates host_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_templates
    ADD CONSTRAINT host_templates_pkey PRIMARY KEY (id);


--
-- Name: idx_host_templates_host; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_host_templates_host ON public.host_templates USING btree (host_id);


--
-- Name: idx_host_templates_template; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_host_templates_template ON public.host_templates USING btree (template_id);


--
-- Name: host_templates host_templates_host_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_templates
    ADD CONSTRAINT host_templates_host_id_fkey FOREIGN KEY (host_id) REFERENCES public.hosts(id) ON DELETE CASCADE;


--
-- Name: host_templates host_templates_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_templates
    ADD CONSTRAINT host_templates_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.templates(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 7AfmxffBcVNuhxR5G1faiKjNye4EV9xW54FWHmzJNXSjxnRYb9fMMAHkl9I4CrN

