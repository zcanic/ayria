/**
 * Shared API payload placeholders.
 *
 * As the runtime stabilizes, promote duplicated request/response types here so
 * front-end changes stay synchronized with backend contracts.
 */

export type SendChatRequest = {
  text: string;
  imagePaths?: string[];
};
