CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  full_name TEXT,
  status TEXT DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  provider_user_id TEXT,
  provider TEXT,
  role_id INTEGER,
  FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE TABLE roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  description TEXT
);

CREATE TABLE permissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  description TEXT
);

CREATE TABLE role_permissions (
  role_id INTEGER,
  permission_id INTEGER,
  PRIMARY KEY (role_id, permission_id),
  FOREIGN KEY (role_id) REFERENCES roles(id),
  FOREIGN KEY (permission_id) REFERENCES permissions(id)
);

CREATE TABLE user_signatures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  signature_image_path TEXT NOT NULL,
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);


CREATE TABLE request_types (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  form_schema JSON,
  template_doc_path TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type_id INTEGER NOT NULL,
  requester_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  form_data JSON,
  status TEXT DEFAULT 'draft',
  final_document_path TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (type_id) REFERENCES request_types(id),
  FOREIGN KEY (requester_id) REFERENCES users(id)
);

CREATE TABLE approval_workflows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_type_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  FOREIGN KEY (request_type_id) REFERENCES request_types(id)
);

CREATE TABLE approval_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id INTEGER NOT NULL,
  step_order INTEGER NOT NULL,
  approver_role_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  FOREIGN KEY (workflow_id) REFERENCES approval_workflows(id),
  FOREIGN KEY (approver_role_id) REFERENCES roles(id)
);

CREATE TABLE request_approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL,
  step_id INTEGER NOT NULL,
  approver_id INTEGER,
  status TEXT DEFAULT 'pending',
  comments TEXT,
  approved_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (request_id) REFERENCES requests(id),
  FOREIGN KEY (step_id) REFERENCES approval_steps(id),
  FOREIGN KEY (approver_id) REFERENCES users(id)
);
