/**
 * Module workspace service.
 *
 * Defines responsibilities and integration points for services.
 */

import apiClient from './apiClient';

async function getWorkspace() {
  const response = await apiClient.get('/workspace/');
  return response.data;
}

async function createWorkspace(data) {
  const response = await apiClient.post('/workspace/', data);
  return response.data;
}

async function updateWorkspace(data) {
  const response = await apiClient.patch('/workspace/', data);
  return response.data;
}

async function getWorkspaceMembers() {
  const response = await apiClient.get('/workspace/members/');
  return response.data;
}

async function leaveWorkspace() {
  await apiClient.delete('/workspace/leave');
}

async function createInvite(email) {
  const response = await apiClient.post('/workspace/invite', { email });
  return response.data;
}

async function listInvites() {
  const response = await apiClient.get('/workspace/invites');
  return response.data;
}

async function revokeInvite(inviteId) {
  await apiClient.delete(`/workspace/invites/${inviteId}`);
}

async function acceptInvite(token) {
  const response = await apiClient.post(`/workspace/accept-invite/${token}`);
  return response.data;
}

export default {
  getWorkspace,
  createWorkspace,
  updateWorkspace,
  getWorkspaceMembers,
  leaveWorkspace,
  createInvite,
  listInvites,
  revokeInvite,
  acceptInvite,
};
