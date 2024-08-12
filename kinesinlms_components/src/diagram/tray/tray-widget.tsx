import * as React from 'react';
import './tray-widget.module.scss'


interface TrayWidgetProps {
	children?: React.ReactNode;
  }
  

export class TrayWidget extends React.Component<TrayWidgetProps> {
	render() {
		return <div className="tray">
			{this.props.children}
		</div>;
	}
}
