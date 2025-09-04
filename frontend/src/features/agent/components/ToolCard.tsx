import { useTranslation } from 'react-i18next';
import React, { useCallback, useMemo, useState } from 'react';
import { AgentToolState } from '../xstates/agentThink';
import { JSONTree } from 'react-json-tree';
import {
  PiCaretDown,
  PiCaretUp,
  PiCheckCircle,
  PiCircleNotch,
  PiLinkBold,
  PiXCircle,
} from 'react-icons/pi';
import { twMerge } from 'tailwind-merge';
import useToolCardExpand from '../hooks/useToolCardExpand';
import { AgentToolResultContent, RelatedDocument } from '../../../@types/conversation';
import { getAgentName } from '../functions/formatDescription';
import RelatedDocumentViewer from '../../../components/RelatedDocumentViewer';

// Theme of JSONTree
// NOTE: need to set the theme as base16 style
const THEME = {
  scheme: 'aws',
  author: 'aws',
  base00: '#f1f3f3', // AWS Paper
  base01: '#000000',
  base02: '#000000',
  base03: '#000000',
  base04: '#000000',
  base05: '#000000',
  base06: '#000000',
  base07: '#000000',
  base08: '#000000',
  base09: '#000000',
  base0A: '#000000',
  base0B: '#000000',
  base0C: '#000000',
  base0D: '#000000',
  base0E: '#000000',
  base0F: '#000000',
};

type ToolCardProps = {
  className?: string;
  toolUseId: string;
  name: string;
  status: AgentToolState;
  input: { [key: string]: any }; // eslint-disable-line @typescript-eslint/no-explicit-any
  resultContents?: AgentToolResultContent[];
  relatedDocuments?: RelatedDocument[];
};

const ToolCard: React.FC<ToolCardProps> = ({
  className,
  toolUseId,
  name,
  status,
  input,
  resultContents,
  relatedDocuments,
}) => {
  const { t } = useTranslation();

  // To avoid re-rendering of all ToolCard components when scrolling, we use a custom hook to manage the expanded state.
  const {
    expandedTools,
    inputExpandedTools,
    contentExpandedTools,
    toggleExpand,
    toggleInputExpand,
    toggleContentExpand,
  } = useToolCardExpand();

  const isExpanded = expandedTools[toolUseId] ?? false;
  const isInputExpanded = inputExpandedTools[toolUseId] ?? false;
  const isContentExpanded = contentExpandedTools[toolUseId] ?? false;

  const handleToggleExpand = useCallback(() => {
    toggleExpand(toolUseId);
  }, [toggleExpand, toolUseId]);

  const handleToggleInputExpand = useCallback(() => {
    toggleInputExpand(toolUseId);
  }, [toggleInputExpand, toolUseId]);

  const handleToggleContentExpand = useCallback(() => {
    toggleContentExpand(toolUseId);
  }, [toggleContentExpand, toolUseId]);

  const displayDocuments = useMemo(() => {
    let documents = relatedDocuments;
    if (documents == null && resultContents != null) {
      // For backward compatibility
      if (resultContents.length === 1 && 'text' in resultContents[0]) {
        // Convert output content text to JSON object if possible.
        try {
          const json = JSON.parse(resultContents[0].text);
          if (Array.isArray(json)) {
            documents = json.map((content, index) => {
              if (typeof content === 'object') {
                return {
                  content: {
                    json: content,
                  },
                  sourceId: `${toolUseId}@${index}`,
                  sourceName: name,
                  sourceLink: content.source_link || undefined,
                };
              } else {
                return {
                  content: {
                    text: String(content),
                  },
                  sourceId: `${toolUseId}@${index}`,
                  sourceName: name,
                };
              }
            });
          } else if (typeof json === 'object') {
            documents = [{
              content: {
                json: json,
              },
              sourceId: toolUseId,
              sourceName: name,
              sourceLink: json.source_link || undefined,
            }];
          } else {
            documents = [{
              content: {
                text: String(json),
              },
              sourceId: toolUseId,
              sourceName: name,
            }];
          }
        } catch {
          documents = [{
            content: resultContents[0],
            sourceId: toolUseId,
            sourceName: name,
          }];
        }
      } else {
        documents = resultContents.map((content, index) => ({
          content: content,
          sourceId: `${toolUseId}@${index}`,
          sourceName: name,
        }));
      }
    }
    if (documents == null || documents.length === 0) {
      return undefined;
    }
    return documents;
  }, [relatedDocuments, resultContents, toolUseId, name]);

  const [viewingRelatedDocument, setViewingRelatedDocument] = useState<RelatedDocument>();

  const ToolResultDocument: React.FC<{
    relatedDocument: RelatedDocument;
  }> = ({
    relatedDocument: document,
  }) => {
    return (
      <div className="flex flex-col">
        {document.sourceName && document.sourceName !== name && (
          <div className="font-semibold break-all line-clamp-1">
            {document.sourceName}
          </div>
        )}
        {document.sourceLink && (
          <span
            className="italic break-all line-clamp-1 cursor-pointer underline"
            onClick={() => window.open(document.sourceLink, '_blank')}
          >
            {document.sourceLink}
          </span>
        )}
        {'text' in document.content && (
          <div className="break-all line-clamp-2 dark:text-aws-font-color-dark">
            {document.content.text}
          </div>
        )}
        {'json' in document.content && (
          <JSONTree
            data={document.content.json}
            theme={{
              extend: THEME,
              tree: ({ style }) => ({
                style: {
                  ...style,
                  margin: 0,
                },
              }),
              value: ({ style }) => ({
                style: {
                  ...style,
                  paddingTop: 0,
                  marginLeft: 0,
                },
              }),
            }}
            invertTheme={false} // disable dark theme
            shouldExpandNodeInitially={() => false}
          />
        )}
        {'json' in document.content && 
         (document.content as any).json && 
         typeof (document.content as any).json === 'object' && 
         'format' in (document.content as any).json && 
         'name' in (document.content as any).json && 
         'document' in (document.content as any).json && (
          <div className="flex items-center space-x-2">
            <div className="break-all line-clamp-1 dark:text-aws-font-color-dark">
              📄 {(document.content as any).json.name}.{(document.content as any).json.format}
            </div>
            <button
              className="px-3 py-1 text-xs bg-aws-sea-blue-light text-white rounded hover:bg-aws-sea-blue-hover-light dark:bg-aws-sea-blue-dark dark:hover:bg-aws-sea-blue-hover-dark"
              onClick={() => {
                try {
                  const docData = (document.content as any).json;
                  const byteCharacters = atob(docData.document);
                  const byteNumbers = new Array(byteCharacters.length);
                  for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                  }
                  const byteArray = new Uint8Array(byteNumbers);
                  
                  const mimeTypes: { [key: string]: string } = {
                    'xls': 'application/vnd.ms-excel',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'html': 'text/html',
                    'pdf': 'application/pdf',
                    'txt': 'text/plain',
                    'csv': 'text/csv',
                    'md': 'text/markdown'
                  };
                  
                  const mimeType = mimeTypes[docData.format] || 'application/octet-stream';
                  const blob = new Blob([byteArray], { type: mimeType });
                  const url = window.URL.createObjectURL(blob);
                  const link = window.document.createElement('a');
                  link.href = url;
                  link.download = `${docData.name}.${docData.format}`;
                  window.document.body.appendChild(link);
                  link.click();
                  window.document.body.removeChild(link);
                  window.URL.revokeObjectURL(url);
                } catch (error) {
                  console.error('Error downloading file:', error);
                }
              }}
            >
              Download
            </button>
          </div>
        )}
        {'json' in document.content && 
         (document.content as any).json && 
         typeof (document.content as any).json === 'object' && 
         'media_type' in (document.content as any).json && 
         'image_data' in (document.content as any).json && 
         (document.content as any).json.media_type === 'image' && (
          <div className="flex flex-col space-y-2">
            <img 
              src={`data:image/png;base64,${(document.content as any).json.image_data}`}
              alt="Generated image"
              className="max-w-full h-auto rounded-lg border border-gray-300 dark:border-gray-600"
              style={{ maxHeight: '400px', objectFit: 'contain' }}
            />
            {document.sourceLink && (
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">🖼️ Generated Image</span>
                <button
                  className="px-3 py-1 text-xs bg-aws-sea-blue-light text-white rounded hover:bg-aws-sea-blue-hover-light dark:bg-aws-sea-blue-dark dark:hover:bg-aws-sea-blue-hover-dark"
                  onClick={() => window.open(document.sourceLink, '_blank')}
                >
                  Download
                </button>
              </div>
            )}
          </div>
        )}
        {'json' in document.content && 
         (document.content as any).json && 
         typeof (document.content as any).json === 'object' && 
         'media_type' in (document.content as any).json && 
         (document.content as any).json.media_type === 'video' && (
          <div className="flex flex-col space-y-2">
            {document.sourceLink && (
              <video 
                controls
                className="max-w-full h-auto rounded-lg border border-gray-300 dark:border-gray-600"
                style={{ maxHeight: '400px' }}
              >
                <source src={document.sourceLink} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            )}
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">🎥 Generated Video</span>
              {document.sourceLink && (
                <button
                  className="px-3 py-1 text-xs bg-aws-sea-blue-light text-white rounded hover:bg-aws-sea-blue-hover-light dark:bg-aws-sea-blue-dark dark:hover:bg-aws-sea-blue-hover-dark"
                  onClick={() => window.open(document.sourceLink, '_blank')}
                >
                  Download
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={twMerge('relative', className)}>
      <div
        className="flex cursor-pointer items-center justify-between p-2 dark:text-aws-font-color-dark hover:bg-light-gray dark:hover:bg-aws-font-color-dark/10"
        onClick={handleToggleExpand}>
        <div className="flex items-center text-base">
          {status === 'running' && (
            <PiCircleNotch className="mr-2 animate-spin text-aws-aqua" />
          )}
          {status === 'success' && (
            <PiCheckCircle className="mr-2 text-aws-aqua" />
          )}
          {status === 'error' && <PiXCircle className="mr-2  text-red" />}
          <h3 className="">{getAgentName(name, t)}</h3>
        </div>
        <div>
          {isExpanded ? (
            <PiCaretUp className="text-lg" />
          ) : (
            <PiCaretDown className="text-lg" />
          )}
        </div>
      </div>

      <div
        className={twMerge(
          `origin-top overflow-hidden transition-transform duration-200 ease-in-out`,
          isExpanded ? 'max-h-full scale-y-100 px-2 pb-2' : 'max-h-0 scale-y-0'
        )}>
        {input && (
          <div>
            <div
              className="mt-2 flex cursor-pointer items-center text-sm"
              onClick={handleToggleInputExpand}>
              <p className="font-bold dark:text-aws-font-color-dark">{t('agent.progressCard.toolInput')}</p>
              {isInputExpanded ? (
                <PiCaretDown className="ml-2" />
              ) : (
                <PiCaretUp className="ml-2" />
              )}
            </div>

            <div
              className={twMerge(
                `overflow-hidden transition-all duration-300 ease-in-out`,
                'dark:text-aws-font-color-dark',
                isInputExpanded ? 'max-h-full ' : 'max-h-0'
              )}>
              <div className="ml-4 mt-2 text-sm">
                <ul className="list-disc">
                  {Object.entries(input).map(([key, value]) => (
                    <li key={key}>
                      <span className="font-semibold">{key}:</span> {
                        typeof value === 'object' && value !== null 
                          ? JSON.stringify(value, null, 2)
                          : String(value)
                      }
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {(status === 'success' || status === 'error') && displayDocuments && (
          <div>
            <div
              className="mt-2 flex cursor-pointer items-center text-sm"
              onClick={handleToggleContentExpand}>
              <p className="font-bold dark:text-aws-font-color-dark">{t('agent.progressCard.toolOutput')}</p>
              {isContentExpanded ? (
                <PiCaretDown className="ml-2" />
              ) : (
                <PiCaretUp className="ml-2" />
              )}
            </div>

            <div
              className={twMerge(
                `overflow-hidden transition-all duration-300 ease-in-out`,
                isContentExpanded ? 'max-h-full' : 'max-h-0'
              )}>
              <div className="flex flex-col ml-2 mt-2 text-sm space-y-1">
                {displayDocuments.length == 1 && (
                  <div className="flex items-center space-x-2">
                    <a
                      className="flex items-center cursor-pointer text-aws-sea-blue-light dark:text-aws-sea-blue-dark hover:text-aws-sea-blue-hover-light dark:hover:text-aws-sea-blue-hover-dark"
                      onClick={() => setViewingRelatedDocument(displayDocuments[0])}
                    >
                      <PiLinkBold />
                    </a>
                    <div className="flex-1">
                      <ToolResultDocument relatedDocument={displayDocuments[0]} />
                    </div>
                  </div>
                )}
                {displayDocuments.length > 1 && displayDocuments.map((document, index) => (
                  <div key={document.sourceId} className="flex items-center space-x-2">
                    <a
                      className="flex items-center cursor-pointer text-aws-sea-blue-light dark:text-aws-sea-blue-dark hover:text-aws-sea-blue-hover-light dark:hover:text-aws-sea-blue-hover-dark"
                      onClick={() => setViewingRelatedDocument(document)}
                    >
                      <div>{`[${index + 1}]`}</div>
                      <PiLinkBold />
                    </a>
                    <div className="flex-1">
                      <ToolResultDocument relatedDocument={document} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
      {viewingRelatedDocument && (
        <RelatedDocumentViewer
          relatedDocument={viewingRelatedDocument}
          onClick={() => {
            setViewingRelatedDocument(undefined);
          }}
        />
      )}
    </div>
  );
};

export default ToolCard;
