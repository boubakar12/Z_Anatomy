//
//  PostUICollectionViewCell.swift
//  A3
//
//  Created by Boubakar Diallo on 11/20/24.
//

import UIKit

class PostUICollectionViewCell: UICollectionViewCell{
    
    private let nameLabel: UILabel = {
        let label = UILabel()
        label.font = UIFont.boldSystemFont(ofSize: 16)
        label.textColor = .black
        return label
    }()
    private let datelabel: UILabel = {
        let label = UILabel()
        label.font = UIFont.systemFont(ofSize: 12)
        label.textColor = .black
        return label
    }()
    private let postImageView: UIImageView = {
        let imageView = UIImageView()
        imageView.contentMode = .scaleAspectFill
        imageView.clipsToBounds = true
        imageView.layer.cornerRadius = 8
        return imageView
    }()
    private let messageLabel: UILabel = {
        let label = UILabel()
        label.font = UIFont.systemFont(ofSize: 14)
        label.textColor = .black
        label.numberOfLines = 0
        return label
    }()
    private let likeBUttom: UIButton = {
        let button = UIButton()
        button.setImage(UIImage(systemName: "heart"), for: .normal)
        return button
    }()
    private let likeslabel: UILabel = {
        let label = UILabel()
        label.font = UIFont.systemFont(ofSize: 12)
        label.textColor =  .black
        return label
    }()
    override init(frame: CGRect){
        super.init(frame: frame)
        setupViews()
    }
    
    required init?(coder: NSCoder) {
        fatalError("init (coder:) has not been implemented")
    }
    
    private func setupViews (){
        addSubview(nameLabel)
        addSubview(datelabel)
        addSubview(postImageView)
        addSubview(messageLabel)
        addSubview(likeBUttom)
        addSubview(likeslabel)
        
        nameLabel.translatesAutoresizingMaskIntoConstraints = false
        nameLabel.topAnchor.constraint(equalTo: topAnchor, constant: 8).isActive = true
        nameLabel.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 8).isActive = true
    }
    
    
    func configure(with post: Post){
        nameLabel.text = post.name
        datelabel.text = post.time.convertToAgo()
        postImageView.image = UIImage(named: "APPDEV") 
        messageLabel.text = post.message
        likeslabel.text = "\(post.likes.count) likes"
        
    }
    
    
    
    
}

