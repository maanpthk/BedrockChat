import React from 'react';
import { useTranslation } from 'react-i18next';
import { Model } from '../@types/conversation';

export type GenerationMode = 'text' | 'image' | 'video';

type Props = {
  mode: GenerationMode;
  onModeChange: (mode: GenerationMode) => void;
  currentModel: Model;
  onModelChange: (model: Model) => void;
  disabled?: boolean;
};

const MediaGenerationModeSelector: React.FC<Props> = ({
  mode,
  onModeChange,
  currentModel,
  onModelChange,
  disabled = false,
}) => {
  const { t } = useTranslation();

  const handleModeChange = (newMode: GenerationMode) => {
    onModeChange(newMode);
    
    // Auto-switch to appropriate model when mode changes
    if (newMode === 'image' && currentModel !== 'amazon-nova-canvas') {
      onModelChange('amazon-nova-canvas');
    } else if (newMode === 'video' && currentModel !== 'amazon-nova-reel') {
      onModelChange('amazon-nova-reel');
    } else if (newMode === 'text' && (currentModel === 'amazon-nova-canvas' || currentModel === 'amazon-nova-reel')) {
      onModelChange('amazon-nova-pro'); // Default to Nova Pro for text
    }
  };

  const modes = [
    { key: 'text' as const, label: t('generationMode.text'), icon: '💬' },
    { key: 'image' as const, label: t('generationMode.image'), icon: '🖼️' },
    { key: 'video' as const, label: t('generationMode.video'), icon: '🎬' },
  ];

  return (
    <div className="flex items-center space-x-2 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {t('generationMode.label')}:
      </span>
      <div className="flex space-x-1">
        {modes.map((modeOption) => (
          <button
            key={modeOption.key}
            onClick={() => handleModeChange(modeOption.key)}
            disabled={disabled}
            className={`
              px-3 py-1 text-sm rounded-md transition-colors flex items-center space-x-1
              ${mode === modeOption.key
                ? 'bg-blue-500 text-white'
                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'
              }
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            <span>{modeOption.icon}</span>
            <span>{modeOption.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default MediaGenerationModeSelector;