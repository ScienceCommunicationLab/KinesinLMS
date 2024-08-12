import * as React from 'react';
import styled from '@emotion/styled';
import {css, Global} from '@emotion/react';

export interface CanvasWidgetProps {
    color?: string;
    background?: string;
}

namespace S {
    export const Container = styled.div<{ color: string; background: string }>`
		height: 100%;
		background-color: ${(p) => p.background};
		background-size: 50px 50px;
		display: flex;
		flex-direction: column;
		flex-grow: 1;

		.react-canvas {
			display: flex;
			flex-grow: 1
		}

		> * {
			height: 100%;
			min-height: 100%;
			width: 100%;
		}

		background-image: linear-gradient(
				0deg,
				transparent 24%,
				${(p) => p.color} 25%,
				${(p) => p.color} 26%,
				transparent 27%,
				transparent 74%,
				${(p) => p.color} 75%,
				${(p) => p.color} 76%,
				transparent 77%,
				transparent
			),
			linear-gradient(
				90deg,
				transparent 24%,
				${(p) => p.color} 25%,
				${(p) => p.color} 26%,
				transparent 27%,
				transparent 74%,
				${(p) => p.color} 75%,
				${(p) => p.color} 76%,
				transparent 77%,
				transparent
			);
	`;

    export const Expand = css`
		html,
		body,
		#root {
			height: 100%;
		}
	`;
}

export class DiagramCanvasWidget extends React.Component<CanvasWidgetProps> {
    /**
     * Clearing all selections can prevent accidentally dragging text elements into the canvas.
     */
    clearSelections = () => {
        window.getSelection()?.removeAllRanges();
    }

    render() {
        return (
            <>
                <Global styles={S.Expand}/>
                <S.Container
                    background={this.props.background || 'rgb(255, 255, 255)'}
                    onMouseDown={this.clearSelections}
                    onTouchStart={this.clearSelections}
                    color={this.props.color || 'rgba(0,0,0, 0.02)'}
                >
                    {this.props.children}
                </S.Container>
            </>
        );
    }
}
