import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ulid } from 'ulid';
import MediaGenerationModeSelector, { GenerationMode } from './MediaGenerationModeSelector';
import ImageGenerationForm from './ImageGenerationForm';
import VideoGenerationForm from './VideoGenerationForm';
import { useMediaGeneration } from '../hooks/useMediaGeneration';
import { useSnackbar } from '../hooks/useSnackbar';
import {
  Model,
  ImageGenerationRequestContent,
  VideoGenerationRequestContent,
  ChatOutput,
} from '../@types/conversation';

type Props = {
  currentModel: Model;
  onModelChange: (model: Model) => void;
  botId?: string;
  onGenerationComplete?: (result: ChatOutput) => void;
  disabled?: boolean;
};

const MediaGenerationInterface: React.FC<Props> = ({
  currentModel,
  onModelChange,
  botId,
  onGenerationComplete,
  disabled = false,
}) => {
  const { t } = useTranslation();
  const { generateImage, generateVideo } = useMediaGeneration();
  const { showSnackbar } = useSnackbar();
  
  const [mode, setMode] = useState<GenerationMode>('text');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleImageGeneration = async (request: ImageGenerationRequestContent) => {
    if (isGenerating) return;
    
    setIsGenerating(true);
    try {
      const conversationId = ulid();
      const result = await generateImage(conversationId, request, botId);
      
      if (onGenerationComplete) {
        onGenerationComplete(result);
      }
      
      showSnackbar(t('imageGeneration.success'));
    } catch (error) {
      console.error('Image generation failed:', error);
      showSnackbar(t('imageGeneration.error'), 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleVideoGeneration = async (request: VideoGenerationRequestContent) => {
    if (isGenerating) return;
    
    setIsGenerating(true);
    try {
      const conversationId = ulid();
      const result = await generateVideo(conversationId, request, botId);
      
      if (onGenerationComplete) {
        onGenerationComplete(result);
      }
      
      showSnackbar(t('videoGeneration.success'));
    } catch (error) {
      console.error('Video generation failed:', error);
      showSnackbar(t('videoGeneration.error'), 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleModeChange = (newMode: GenerationMode) => {
    if (isGenerating) return;
    setMode(newMode);
  };

  // Don't show media generation interface for text mode
  if (mode === 'text') {
    return (
      <MediaGenerationModeSelector
        mode={mode}
        onModeChange={handleModeChange}
        currentModel={currentModel}
        onModelChange={onModelChange}
        disabled={disabled || isGenerating}
      />
    );
  }

  return (
    <div className="space-y-4">
      <MediaGenerationModeSelector
        mode={mode}
        onModeChange={handleModeChange}
        currentModel={currentModel}
        onModelChange={onModelChange}
        disabled={disabled || isGenerating}
      />
      
      {mode === 'image' && (
        <ImageGenerationForm
          onGenerate={handleImageGeneration}
          isGenerating={isGenerating}
        />
      )}
      
      {mode === 'video' && (
        <VideoGenerationForm
          onGenerate={handleVideoGeneration}
          isGenerating={isGenerating}
        />
      )}
    </div>
  );
};

export default MediaGenerationInterface;