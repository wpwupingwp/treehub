--
-- PostgreSQL database dump
--

-- Dumped from database version 14.1
-- Dumped by pg_dump version 14.1

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

--
-- Name: analysisstep_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.analysisstep_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.analysisstep_id_seq OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analysis; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analysis (
    analysisstep_id integer DEFAULT nextval('public.analysisstep_id_seq'::regclass) NOT NULL,
    study_id integer,
    software character varying(255),
    algorithm character varying(255)
);


ALTER TABLE public.analysis OWNER TO postgres;

--
-- Name: analysis_tree; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analysis_tree (
    analysisstep_id integer NOT NULL,
    tree_id integer NOT NULL,
    input boolean NOT NULL
);


ALTER TABLE public.analysis_tree OWNER TO postgres;

--
-- Name: edges; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.edges (
    parent_id integer DEFAULT (0)::regclass NOT NULL,
    child_id integer DEFAULT (0)::regclass NOT NULL,
    edge_length numeric,
    edge_support numeric
);


ALTER TABLE public.edges OWNER TO postgres;

--
-- Name: matrix_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.matrix_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.matrix_id_seq OWNER TO postgres;

--
-- Name: matrix; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.matrix (
    matrix_id integer DEFAULT nextval('public.matrix_id_seq'::regclass) NOT NULL,
    title character varying(255),
    "nchar" integer,
    ntax integer,
    analysisstep_id integer NOT NULL,
    legacy_id character varying(35),
    description character varying(255),
    input boolean
);


ALTER TABLE public.matrix OWNER TO postgres;

--
-- Name: ncbi_map_id; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ncbi_map_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ncbi_map_id OWNER TO postgres;

--
-- Name: ncbi_map; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ncbi_map (
    node_id integer,
    tax_id integer,
    rank integer,
    tree_id integer,
    ncbi_map_id integer DEFAULT nextval('public.ncbi_map_id'::regclass) NOT NULL
);


ALTER TABLE public.ncbi_map OWNER TO postgres;

--
-- Name: ncbi_names; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ncbi_names (
    tax_id integer NOT NULL,
    name_txt character varying(255) NOT NULL,
    unique_name character varying(255),
    name_class character varying(32)
);


ALTER TABLE public.ncbi_names OWNER TO postgres;

--
-- Name: ncbi_node_path; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ncbi_node_path (
    child_path_id bigint DEFAULT (0)::bigint NOT NULL,
    parent_path_id bigint DEFAULT (0)::bigint NOT NULL,
    distance integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.ncbi_node_path OWNER TO postgres;

--
-- Name: ncbi_nodes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ncbi_nodes (
    tax_id integer NOT NULL,
    parent_tax_id integer NOT NULL,
    rank character varying(32),
    embl_code character varying(16),
    division_id integer NOT NULL,
    inherited_div_flag integer NOT NULL,
    genetic_code_id integer NOT NULL,
    inherited_gc_flag integer NOT NULL,
    mitochondrial_genetic_code_id integer NOT NULL,
    inherited_mgc_flag integer NOT NULL,
    genbank_hidden_flag integer NOT NULL,
    hidden_subtree_root_flag integer NOT NULL,
    comments character varying(255) DEFAULT NULL::character varying,
    left_id integer NOT NULL,
    right_id integer NOT NULL
);


ALTER TABLE public.ncbi_nodes OWNER TO postgres;

--
-- Name: node_path; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.node_path (
    child_path_id integer DEFAULT (0)::regclass NOT NULL,
    parent_path_id integer DEFAULT (0)::regclass NOT NULL,
    distance integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.node_path OWNER TO postgres;

--
-- Name: nodes_node_id; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.nodes_node_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.nodes_node_id OWNER TO postgres;

--
-- Name: nodes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.nodes (
    node_id integer DEFAULT nextval('public.nodes_node_id'::regclass) NOT NULL,
    node_label character varying(255),
    left_id integer DEFAULT (0)::regclass,
    right_id integer DEFAULT (0)::regclass,
    tree_id integer DEFAULT (0)::regclass,
    taxon_variant_id integer,
    legacy_id character varying(35),
    ncbi_map integer,
    designated_tax_id integer
);


ALTER TABLE public.nodes OWNER TO postgres;

--
-- Name: study_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.study_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.study_id_seq OWNER TO postgres;

--
-- Name: study; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.study (
    study_id integer DEFAULT nextval('public.study_id_seq'::regclass) NOT NULL,
    pub_type character varying(30),
    author text,
    year integer,
    title text,
    journal character varying(255),
    s_author text,
    s_title text,
    place_pub character varying(255),
    publisher character varying(255),
    volume character varying(50),
    number character varying(150),
    pages character varying(100),
    isbn character varying(35),
    keywords character varying(255),
    abstract text,
    legacy_id character varying(30),
    url character varying(255),
    doi character varying(100),
    lastmodifieddate date
);


ALTER TABLE public.study OWNER TO postgres;

--
-- Name: taxon_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.taxon_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.taxon_id_seq OWNER TO postgres;

--
-- Name: taxa; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.taxa (
    taxon_id integer DEFAULT nextval('public.taxon_id_seq'::regclass) NOT NULL,
    namebank_id integer,
    namestring character varying(255),
    tax_id integer,
    groupcode integer
);


ALTER TABLE public.taxa OWNER TO postgres;

--
-- Name: taxon_variant_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.taxon_variant_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.taxon_variant_id_seq OWNER TO postgres;

--
-- Name: taxon_variants; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.taxon_variants (
    taxon_variant_id integer DEFAULT nextval('public.taxon_variant_id_seq'::regclass) NOT NULL,
    taxon_id integer,
    namebank_id integer,
    namestring character varying(255),
    fullnamestring character varying(255),
    lexicalqualifier character varying(30)
);


ALTER TABLE public.taxon_variants OWNER TO postgres;

--
-- Name: temp; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.temp AS
 SELECT DISTINCT analysis.analysisstep_id AS analysis_id,
    analysis.study_id,
    analysis.software,
    analysis.algorithm,
    analysis_tree.tree_id
   FROM (public.analysis
     LEFT JOIN public.analysis_tree ON ((analysis.analysisstep_id = analysis_tree.analysisstep_id)))
  ORDER BY analysis.analysisstep_id;


ALTER TABLE public.temp OWNER TO postgres;

--
-- Name: trees_tree_id; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.trees_tree_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.trees_tree_id OWNER TO postgres;

--
-- Name: trees; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trees (
    tree_id integer DEFAULT nextval('public.trees_tree_id'::regclass) NOT NULL,
    legacy_id character varying(255) DEFAULT ''::character varying,
    root integer DEFAULT (0)::regclass NOT NULL,
    tree_label character varying(255),
    tree_title character varying(255),
    tree_type character varying(30),
    tree_kind character varying(30),
    tree_quality character varying(100),
    study_id integer
);


ALTER TABLE public.trees OWNER TO postgres;

--
-- Name: ncbi_map ncbi_map_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ncbi_map
    ADD CONSTRAINT ncbi_map_pkey PRIMARY KEY (ncbi_map_id);


--
-- Name: ncbi_nodes ncbi_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ncbi_nodes
    ADD CONSTRAINT ncbi_nodes_pkey PRIMARY KEY (tax_id);


--
-- Name: nodes nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nodes
    ADD CONSTRAINT nodes_pkey PRIMARY KEY (node_id);


--
-- Name: study study_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.study
    ADD CONSTRAINT study_pkey PRIMARY KEY (study_id);


--
-- Name: taxa taxa_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.taxa
    ADD CONSTRAINT taxa_pkey PRIMARY KEY (taxon_id);


--
-- Name: taxon_variants taxon_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.taxon_variants
    ADD CONSTRAINT taxon_variants_pkey PRIMARY KEY (taxon_variant_id);


--
-- Name: trees trees_b_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trees
    ADD CONSTRAINT trees_b_pkey PRIMARY KEY (tree_id);


--
-- Name: analysisstep_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX analysisstep_id ON public.matrix USING btree (analysisstep_id);


--
-- Name: analysisstep_id_in; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX analysisstep_id_in ON public.analysis_tree USING btree (analysisstep_id);


--
-- Name: edges_child_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX edges_child_id ON public.edges USING btree (child_id);


--
-- Name: edges_parent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX edges_parent_id ON public.edges USING btree (parent_id);


--
-- Name: fullnamestring; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fullnamestring ON public.taxon_variants USING btree (fullnamestring);


--
-- Name: lexicalqualifier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lexicalqualifier ON public.taxon_variants USING btree (lexicalqualifier);


--
-- Name: ncbi_names_idx_name_class; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_names_idx_name_class ON public.ncbi_names USING btree (name_class);


--
-- Name: ncbi_names_idx_name_txt; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_names_idx_name_txt ON public.ncbi_names USING btree (name_txt);


--
-- Name: ncbi_names_idx_tax_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_names_idx_tax_id ON public.ncbi_names USING btree (tax_id);


--
-- Name: ncbi_node_path_child_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_node_path_child_id ON public.ncbi_node_path USING btree (parent_path_id);


--
-- Name: ncbi_node_path_distance; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_node_path_distance ON public.ncbi_node_path USING btree (distance);


--
-- Name: ncbi_node_path_parent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_node_path_parent_id ON public.ncbi_node_path USING btree (child_path_id);


--
-- Name: ncbi_nodes_idx_left_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_nodes_idx_left_id ON public.ncbi_nodes USING btree (left_id);


--
-- Name: ncbi_nodes_idx_parent_tax_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_nodes_idx_parent_tax_id ON public.ncbi_nodes USING btree (parent_tax_id);


--
-- Name: ncbi_nodes_idx_right_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ncbi_nodes_idx_right_id ON public.ncbi_nodes USING btree (right_id);


--
-- Name: nchar; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "nchar" ON public.matrix USING btree ("nchar");


--
-- Name: node_path_child_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX node_path_child_id ON public.node_path USING btree (child_path_id);


--
-- Name: node_path_distance; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX node_path_distance ON public.node_path USING btree (distance);


--
-- Name: node_path_parent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX node_path_parent_id ON public.node_path USING btree (parent_path_id);


--
-- Name: nodes_idx_designated_tax_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX nodes_idx_designated_tax_id ON public.nodes USING btree (designated_tax_id);


--
-- Name: nodes_left_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX nodes_left_id ON public.nodes USING btree (left_id);


--
-- Name: nodes_ncbi_map; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX nodes_ncbi_map ON public.nodes USING btree (ncbi_map);


--
-- Name: nodes_node_id_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX nodes_node_id_key ON public.nodes USING btree (node_id);


--
-- Name: nodes_node_label; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX nodes_node_label ON public.nodes USING btree (node_label);


--
-- Name: nodes_right_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX nodes_right_id ON public.nodes USING btree (right_id);


--
-- Name: nodes_tree_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX nodes_tree_id ON public.nodes USING btree (tree_id);


--
-- Name: ntax; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ntax ON public.matrix USING btree (ntax);


--
-- Name: t_namebank_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX t_namebank_id ON public.taxa USING btree (namebank_id);


--
-- Name: tax_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX tax_id ON public.taxa USING btree (tax_id);


--
-- Name: taxon_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX taxon_id ON public.taxon_variants USING btree (taxon_id);


--
-- Name: tree_id_in; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX tree_id_in ON public.analysis_tree USING btree (tree_id);


--
-- Name: trees_study_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX trees_study_id ON public.trees USING btree (study_id);


--
-- Name: trees_tree_id_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX trees_tree_id_key ON public.trees USING btree (tree_id);


--
-- Name: tv_namebank_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX tv_namebank_id ON public.taxon_variants USING btree (namebank_id);


--
-- Name: tv_namestring; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX tv_namestring ON public.taxon_variants USING btree (namestring);


--
-- Name: edges child_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.edges
    ADD CONSTRAINT child_id_fk FOREIGN KEY (child_id) REFERENCES public.nodes(node_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: nodes tree_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nodes
    ADD CONSTRAINT tree_id_fk FOREIGN KEY (tree_id) REFERENCES public.trees(tree_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

