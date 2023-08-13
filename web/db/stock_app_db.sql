--
-- PostgreSQL database dump
--

-- Dumped from database version 14.3
-- Dumped by pg_dump version 14.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: optimum_symbol_parameters; Type: TABLE; Schema: public; Owner: stock_app
--

CREATE TABLE public.optimum_symbol_parameters (
    symbol_id integer NOT NULL,
    symbol character varying,
    last_updated character varying,
    calc_period character varying,
    single_param_optimum_window integer,
    single_param_optimum_multiple numeric,
    multi_param_optimum_window_1 integer,
    multi_param_optimum_window_2 integer,
    multi_param_optimum_multiple numeric,
    organic_growth numeric,
    exp_ma_optimum_window integer,
    exp_ma_optimum_multiple numeric
);


ALTER TABLE public.optimum_symbol_parameters OWNER TO stock_app;

--
-- Name: optimum_symbol_parameters_symbol_id_seq; Type: SEQUENCE; Schema: public; Owner: stock_app
--

CREATE SEQUENCE public.optimum_symbol_parameters_symbol_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.optimum_symbol_parameters_symbol_id_seq OWNER TO stock_app;

--
-- Name: optimum_symbol_parameters_symbol_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: stock_app
--

ALTER SEQUENCE public.optimum_symbol_parameters_symbol_id_seq OWNED BY public.optimum_symbol_parameters.symbol_id;


--
-- Name: optimum_symbol_parameters symbol_id; Type: DEFAULT; Schema: public; Owner: stock_app
--

ALTER TABLE ONLY public.optimum_symbol_parameters ALTER COLUMN symbol_id SET DEFAULT nextval('public.optimum_symbol_parameters_symbol_id_seq'::regclass);


--
-- PostgreSQL database dump complete
--

