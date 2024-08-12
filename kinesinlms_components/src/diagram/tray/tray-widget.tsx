import * as React from 'react';
import './tray-widget.module.scss'


export class TrayWidget extends React.Component {
	render() {
		return <div className="tray">
			{this.props.children}
		</div>;
	}
}
