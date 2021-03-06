import React, {Component} from 'react';
import styles from '../styles/TypeaheadMenuItem.css';
import {MenuItem} from 'react-bootstrap-typeahead';
import isEqual from 'lodash/isEqual';
import ImageCropDin from 'material-ui/svg-icons/image/crop-din';
import ActionRoom from 'material-ui/svg-icons/action/room';

export class TypeaheadMenuItem extends Component {

    constructor(props) {
        super(props);
        this.createDescription = this.createDescription.bind(this);
    }

    createDescription(result) {
        let description = [];
        result.adminName2 ? description.push(result.adminName2): null;
        result.adminName1 ? description.push(result.adminName1): null;
        result.countryName ? description.push(result.countryName): null;

        return description.join(', ');
    }

    render() {
        return (
            <MenuItem option={this.props.result} position={this.props.index} className={styles.menuItem}>
                <div className={styles.menuItemIconDiv}>
                    {this.props.result.bbox && !isEqual(this.props.result.bbox, {}) 
                    ?
                    <ImageCropDin className={styles.menuItemIcon}/>
                    : 
                    <ActionRoom className={styles.menuItemIcon}/>
                    }
                </div>
                <div className={styles.menuItemText}><strong>{this.props.result.name}</strong></div>
                <div className={styles.menuItemText}>{this.createDescription(this.props.result)}</div>
            </MenuItem>
        )
    }
}

TypeaheadMenuItem.propTypes = {
    result: React.PropTypes.object,
    index: React.PropTypes.number,
}

export default TypeaheadMenuItem;
