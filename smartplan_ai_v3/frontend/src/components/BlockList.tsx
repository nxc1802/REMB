'use client';

import React from 'react';
import { BlockInfo } from '@/types/api';

interface BlockListProps {
    blocks: BlockInfo[];
    selectedBlockId?: string;
    onBlockSelect: (block: BlockInfo) => void;
}

export default function BlockList({
    blocks,
    selectedBlockId,
    onBlockSelect,
}: BlockListProps) {
    const formatArea = (area: number): string => {
        if (area >= 10000) {
            return `${(area / 10000).toFixed(2)} ha`;
        }
        return `${area.toFixed(0)} m²`;
    };

    return (
        <div className="bg-gray-900 rounded-lg border border-gray-700 p-4">
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <span className="text-xl">📦</span>
                Blocks ({blocks.length})
            </h3>

            {blocks.length === 0 ? (
                <div className="text-center text-gray-500 py-4">
                    <p>Chưa có blocks</p>
                    <p className="text-sm mt-1">Upload DXF hoặc set boundary</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {blocks.map((block) => (
                        <button
                            key={block.id}
                            onClick={() => onBlockSelect(block)}
                            className={`w-full text-left p-3 rounded-lg transition-colors ${block.id === selectedBlockId
                                    ? 'bg-yellow-600/30 border border-yellow-500'
                                    : 'bg-gray-800 border border-gray-700 hover:border-gray-500'
                                }`}
                        >
                            <div className="flex justify-between items-center">
                                <span className="font-medium text-white">{block.id}</span>
                                <span className="text-sm text-gray-400">
                                    {formatArea(block.area)}
                                </span>
                            </div>

                            {block.assets.length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-1">
                                    {block.assets.map((asset, idx) => (
                                        <span
                                            key={idx}
                                            className="text-xs px-2 py-0.5 bg-gray-700 rounded text-gray-300"
                                        >
                                            {asset.type}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
