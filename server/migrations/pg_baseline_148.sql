
CREATE TABLE admins (
	id SERIAL NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	password_hash VARCHAR(128) NOT NULL, 
	nickname VARCHAR(64), 
	role_id INTEGER NOT NULL, 
	is_active BOOLEAN, 
	last_login TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id)
)




CREATE TABLE ai_providers (
	id SERIAL NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	base_url VARCHAR(255) NOT NULL, 
	api_key TEXT, 
	models TEXT NOT NULL, 
	enabled INTEGER, 
	sort_order INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)




CREATE TABLE analyses (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	date VARCHAR(10) NOT NULL, 
	kind VARCHAR(16), 
	mode VARCHAR(8), 
	score FLOAT, 
	summary TEXT, 
	ntrp VARCHAR(8), 
	report TEXT, 
	thumb TEXT, 
	highlights TEXT, 
	video_url VARCHAR(255), 
	pose TEXT, 
	status VARCHAR(16) NOT NULL, 
	pipeline_status TEXT, 
	created_at FLOAT, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)




CREATE TABLE analysis_video_info (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	analysis_id INTEGER, 
	source_file_id INTEGER, 
	playback_file_id INTEGER, 
	cut_info TEXT, 
	derivatives TEXT, 
	created_at FLOAT, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_analysis_video_info_analysis_id UNIQUE (analysis_id), 
	FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE SET NULL, 
	FOREIGN KEY(source_file_id) REFERENCES files (id) ON DELETE SET NULL, 
	FOREIGN KEY(playback_file_id) REFERENCES files (id) ON DELETE SET NULL
)




CREATE TABLE checkins (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id VARCHAR(64) NOT NULL, 
	date VARCHAR(10) NOT NULL, 
	created_at FLOAT, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)




CREATE TABLE diaries (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	date VARCHAR(10) NOT NULL, 
	time VARCHAR(5), 
	type VARCHAR(16), 
	duration INTEGER, 
	intensity INTEGER, 
	mood INTEGER, 
	costs TEXT, 
	gears TEXT, 
	notes TEXT, 
	created_at FLOAT, 
	business_time FLOAT, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)




CREATE TABLE event_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	level VARCHAR(16) NOT NULL, 
	type VARCHAR(64) NOT NULL, 
	trace_id VARCHAR(64), 
	action VARCHAR(64), 
	message TEXT NOT NULL, 
	stack TEXT, 
	page VARCHAR(256), 
	params TEXT, 
	device_info TEXT, 
	client_time INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)




CREATE TABLE files (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	md5 VARCHAR(32) NOT NULL, 
	original_name VARCHAR(255), 
	rel_path VARCHAR(512) NOT NULL, 
	size_bytes INTEGER, 
	mime_type VARCHAR(128), 
	upload_source VARCHAR(32), 
	business_type VARCHAR(32), 
	business_id INTEGER, 
	ref_count INTEGER, 
	security_checked INTEGER, 
	created_at FLOAT, 
	deleted_at FLOAT, 
	storage VARCHAR(32) DEFAULT 'local' NOT NULL, 
	storage_status INTEGER DEFAULT '0' NOT NULL, 
	PRIMARY KEY (id)
)




CREATE TABLE file_bindings (
	id SERIAL NOT NULL, 
	file_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	business_type VARCHAR(32) NOT NULL, 
	business_id INTEGER NOT NULL, 
	field VARCHAR(64), 
	created_at FLOAT, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_file_binding_target UNIQUE (file_id, business_type, business_id, field), 
	FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE CASCADE
)




CREATE TABLE gears (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	category VARCHAR(32), 
	name VARCHAR(128), 
	buy_date VARCHAR(10), 
	price FLOAT, 
	feeling TEXT, 
	photo TEXT, 
	created_at FLOAT, 
	business_time FLOAT, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)




CREATE TABLE posts (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	date VARCHAR(10) NOT NULL, 
	platform VARCHAR(16), 
	title VARCHAR(256), 
	content TEXT, 
	status VARCHAR(8), 
	created_at FLOAT, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)




CREATE TABLE roles (
	id SERIAL NOT NULL, 
	name VARCHAR(32) NOT NULL, 
	code VARCHAR(32) NOT NULL, 
	description VARCHAR(128), 
	permissions TEXT, 
	is_system BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (name)
)




CREATE TABLE system_configs (
	id SERIAL NOT NULL, 
	key VARCHAR(64) NOT NULL, 
	value TEXT, 
	updated_by INTEGER, 
	created_at FLOAT, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)




CREATE TABLE users (
	id SERIAL NOT NULL, 
	openid VARCHAR(128) NOT NULL, 
	nickname VARCHAR(64), 
	avatar_url VARCHAR(512), 
	gender INTEGER, 
	birthday VARCHAR(10), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)




CREATE TABLE weight_records (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	date VARCHAR(10) NOT NULL, 
	weight FLOAT, 
	bust FLOAT, 
	waist FLOAT, 
	hip FLOAT, 
	created_at FLOAT, 
	business_time FLOAT, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)



CREATE UNIQUE INDEX ix_admins_username ON admins (username)

CREATE UNIQUE INDEX ix_ai_providers_name ON ai_providers (name)

CREATE INDEX ix_analyses_user_id ON analyses (user_id)

CREATE INDEX ix_analysis_video_info_user_id ON analysis_video_info (user_id)

CREATE UNIQUE INDEX ix_analysis_video_info_analysis_id ON analysis_video_info (analysis_id)

CREATE INDEX ix_checkins_user_id ON checkins (user_id)

CREATE INDEX ix_diaries_user_id ON diaries (user_id)

CREATE INDEX ix_event_logs_trace_id ON event_logs (trace_id)

CREATE INDEX ix_event_logs_action ON event_logs (action)

CREATE INDEX ix_event_logs_client_time ON event_logs (client_time)

CREATE INDEX ix_event_logs_created_at ON event_logs (created_at)

CREATE INDEX ix_event_logs_level ON event_logs (level)

CREATE INDEX ix_event_logs_user_id ON event_logs (user_id)

CREATE INDEX ix_files_business_type ON files (business_type)

CREATE INDEX ix_files_md5 ON files (md5)

CREATE INDEX ix_files_rel_path ON files (rel_path)

CREATE INDEX ix_files_business_id ON files (business_id)

CREATE INDEX ix_files_user_id ON files (user_id)

CREATE INDEX ix_files_storage_status ON files (storage_status)

CREATE INDEX ix_files_deleted_at ON files (deleted_at)

CREATE UNIQUE INDEX uq_files_user_md5_active ON files (user_id, md5) WHERE deleted_at IS NULL

CREATE INDEX ix_file_bindings_user_id ON file_bindings (user_id)

CREATE INDEX ix_file_bindings_file_id ON file_bindings (file_id)

CREATE INDEX ix_file_bindings_business_type ON file_bindings (business_type)

CREATE INDEX ix_file_bindings_business_id ON file_bindings (business_id)

CREATE INDEX ix_gears_user_id ON gears (user_id)

CREATE INDEX ix_posts_user_id ON posts (user_id)

CREATE UNIQUE INDEX ix_roles_code ON roles (code)

CREATE UNIQUE INDEX ix_system_configs_key ON system_configs (key)

CREATE UNIQUE INDEX ix_users_openid ON users (openid)

CREATE INDEX ix_weight_records_user_id ON weight_records (user_id)