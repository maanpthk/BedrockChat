import { useCallback } from 'react';
import { useHttp } from './useHttp';
import {
  ChatInput,
  ChatOutput,
  ImageGenerationRequestContent,
  VideoGenerationRequestContent,
} from '../@types/conversation';

export const useMediaGeneration = () => {
  const http = useHttp();

  const generateImage = useCallback(
    async (
      conversationId: string,
      imageRequest: ImageGenerationRequestContent,
      botId?: string
    ): Promise<ChatOutput> => {
      const chatInput: ChatInput = {
        conversationId,
        message: {
          role: 'user',
          content: [imageRequest],
          model: 'amazon-nova-canvas',
          parentMessageId: null,
        },
        botId,
        continueGenerate: false,
        enableReasoning: false,
      };

      const response = await http.post<ChatOutput>('/generate-image', chatInput);
      return response;
    },
    [http]
  );

  const generateVideo = useCallback(
    async (
      conversationId: string,
      videoRequest: VideoGenerationRequestContent,
      botId?: string
    ): Promise<ChatOutput> => {
      const chatInput: ChatInput = {
        conversationId,
        message: {
          role: 'user',
          content: [videoRequest],
          model: 'amazon-nova-reel',
          parentMessageId: null,
        },
        botId,
        continueGenerate: false,
        enableReasoning: false,
      };

      const response = await http.post<ChatOutput>('/generate-video', chatInput);
      return response;
    },
    [http]
  );

  return {
    generateImage,
    generateVideo,
  };
};