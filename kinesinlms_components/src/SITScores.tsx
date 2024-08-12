import React, {PureComponent} from 'react';

interface ScoreProps {
    maxScore: number;
    score: number;
}

export default class SITScores extends PureComponent<ScoreProps> {

    render() {
        return (
            <div className="sit-score">
            {
                this.props.maxScore ? ( 
                    this.props.score 
                        ? `Points received: ${this.props.score} / ${this.props.maxScore}` 
                        : `Points possible: ${this.props.maxScore}`
                ) : null
            }
            </div>
        );
    }
}
