/**
 * Client API orchestrator connecting to backend endpoints.
 */
import { formatPayload, sanitizeInput } from "./formatter.js";

export class ClientAPI {
  constructor(baseUrl = "http://localhost:8000") {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  setToken(token) {
    this.token = sanitizeInput(token);
  }

  buildRequest(endpoint, payload) {
    const cleanPayload = formatPayload(payload);
    return {
      url: `${this.baseUrl}/${endpoint}`,
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
      body: cleanPayload,
    };
  }
}
