import { request } from "./request";

export interface KnowledgeBase { id: string; name: string; description: string; owner_id: string; status: string; created_at: string; updated_at: string; }
export interface KnowledgeDocument { id: string; knowledge_base_id: string; title: string; source_type: string; source_uri: string | null; status: string; current_version_id: string | null; created_at: string; updated_at: string; }
export interface KnowledgeVersion { id: string; document_id: string; version: string; status: string; ingestion_status: string; source_uri: string | null; content_hash: string | null; content_text: string | null; created_by: string; created_at: string; }
export interface KnowledgeChunk { id: string; document_version_id: string; chunk_index: number; content: string; start_offset: number; end_offset: number; }
export interface KnowledgePage<T> { items: T[]; total: number; page: number; page_size: number; }
export interface RetrievalResult { document_id: string; document_version_id: string; chunk_id: string; chunk_index: number; source_document: string; source_uri: string | null; relevance_score: number; citation: string; content: string; }
export interface RetrievalResponse { query: string; top_k: number; results: RetrievalResult[]; }

export const listKnowledgeBases = (page = 1, pageSize = 20) => request.get<KnowledgePage<KnowledgeBase>>("/knowledge", { params: { page, page_size: pageSize } }).then(r => r.data);
export const createKnowledgeBase = (payload: Pick<KnowledgeBase, "name" | "description" | "status">) => request.post<KnowledgeBase>("/knowledge", payload).then(r => r.data);
export const updateKnowledgeBase = (id: string, payload: Partial<Pick<KnowledgeBase, "name" | "description" | "status">>) => request.patch<KnowledgeBase>(`/knowledge/${id}`, payload).then(r => r.data);
export const listDocuments = (knowledgeBaseId: string, page = 1, pageSize = 20) => request.get<KnowledgePage<KnowledgeDocument>>(`/knowledge/${knowledgeBaseId}/documents`, { params: { page, page_size: pageSize } }).then(r => r.data);
export const createDocument = (knowledgeBaseId: string, payload: { title: string; source_type?: string; source_uri?: string | null }) => request.post<KnowledgeDocument>(`/knowledge/${knowledgeBaseId}/documents`, payload).then(r => r.data);
export const updateDocument = (knowledgeBaseId: string, documentId: string, payload: Partial<Pick<KnowledgeDocument, "title" | "source_type" | "source_uri" | "status">>) => request.patch<KnowledgeDocument>(`/knowledge/${knowledgeBaseId}/documents/${documentId}`, payload).then(r => r.data);
export const deleteDocument = (knowledgeBaseId: string, documentId: string) => request.delete(`/knowledge/${knowledgeBaseId}/documents/${documentId}`);
export const listVersions = (knowledgeBaseId: string, documentId: string) => request.get<KnowledgeVersion[]>(`/knowledge/${knowledgeBaseId}/documents/${documentId}/versions`).then(r => r.data);
export const createVersion = (knowledgeBaseId: string, documentId: string, payload: { version: string; source_uri?: string | null; content_hash?: string | null; content_text?: string | null; status?: string }) => request.post<KnowledgeVersion>(`/knowledge/${knowledgeBaseId}/documents/${documentId}/versions`, payload).then(r => r.data);
export const ingestVersion = (versionId: string, payload?: { max_chars?: number; overlap_chars?: number }) => request.post<{ version_id: string; ingestion_status: string; chunk_count: number; content_hash: string }>(`/knowledge/versions/${versionId}/ingest`, payload).then(r => r.data);
export const listChunks = (versionId: string) => request.get<KnowledgeChunk[]>(`/knowledge/versions/${versionId}/chunks`).then(r => r.data);
export const retrieveKnowledge = (payload: { query: string; top_k?: number; knowledge_base_id?: string; document_id?: string }) => request.post<RetrievalResponse>("/knowledge/retrieve", payload).then(r => r.data);
